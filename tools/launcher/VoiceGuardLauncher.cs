using System;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.Net;
using System.Threading;
using System.Windows.Forms;

namespace VoiceGuardLauncher
{
    internal static class Program
    {
        private static Process _pythonProcess;
        private static Process _edgeProcess;
        private static NotifyIcon _trayIcon;
        private static SplashForm _splashForm;
        private static ApplicationContext _appContext;
        private static readonly object _syncLock = new object();
        private static bool _isExiting = false;

        [STAThread]
        private static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);

            // Обработчики завершения процесса для очистки дерева процессов
            AppDomain.CurrentDomain.ProcessExit += OnProcessExit;
            Application.ApplicationExit += OnProcessExit;

            string baseDir = AppDomain.CurrentDomain.BaseDirectory;
            if (string.IsNullOrEmpty(baseDir))
            {
                baseDir = Directory.GetCurrentDirectory();
            }

            string pythonExe = ResolvePythonPath(baseDir);
            if (string.IsNullOrEmpty(pythonExe))
            {
                MessageBox.Show(
                    "Не удалось обнаружить среду Python для запуска VoiceGuard.\n\n" +
                    "Проверены пути:\n" +
                    "1. runtime\\python.exe (портативный бандл)\n" +
                    "2. .venv\\Scripts\\python.exe (локальное виртуальное окружение)\n" +
                    "3. Системный python.exe в системной переменной PATH\n\n" +
                    "Рекомендация: Создайте окружение командой 'python -m venv .venv' и установите зависимости 'pip install -r requirements.txt'.",
                    "VoiceGuard — Ошибка запуска",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
                return;
            }

            string appScript = Path.Combine(baseDir, "app.py");
            if (!File.Exists(appScript))
            {
                MessageBox.Show(
                    string.Format("Не найден главный файл приложения:\n{0}\n\nУбедитесь, что VoiceGuard.exe находится в корневой папке проекта.", appScript),
                    "VoiceGuard — Файл не найден",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
                return;
            }

            // Запуск Python-сервера в скрытом фоновом режиме
            try
            {
                ProcessStartInfo psi = new ProcessStartInfo
                {
                    FileName = pythonExe,
                    Arguments = "\"" + appScript + "\"",
                    WorkingDirectory = baseDir,
                    CreateNoWindow = true,
                    UseShellExecute = false,
                    WindowStyle = ProcessWindowStyle.Hidden
                };

                _pythonProcess = Process.Start(psi);
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    "Ошибка запуска процесса Python:\n" + ex.Message,
                    "VoiceGuard — Ошибка запуска",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
                return;
            }

            _appContext = new ApplicationContext();

            // Создаем и показываем Splash Screen
            _splashForm = new SplashForm();
            _splashForm.CancelRequested += delegate
            {
                TerminateAll();
            };

            // Фоновый поток ожидания готовности веб-сервера
            Thread pollThread = new Thread(delegate()
            {
                bool ready = WaitForServer("http://127.0.0.1:7860/", 45000, 250);
                if (_isExiting) return;

                if (!ready)
                {
                    if (_splashForm != null && !_splashForm.IsDisposed)
                    {
                        _splashForm.Invoke((Action)delegate
                        {
                            _splashForm.Hide();
                            MessageBox.Show(
                                "Время ожидания ответа веб-сервера VoiceGuard истекло (45 секунд).\n" +
                                "Возможно, при первой загрузке весов нейросети потребовалось больше времени или произошла ошибка в Python.",
                                "VoiceGuard — Превышен таймаут",
                                MessageBoxButtons.OK,
                                MessageBoxIcon.Warning
                            );
                            TerminateAll();
                        });
                    }
                    return;
                }

                // Сервер ответил HTTP 200/OK
                if (_splashForm != null && !_splashForm.IsDisposed)
                {
                    _splashForm.Invoke((Action)delegate
                    {
                        _splashForm.Close();
                        _splashForm = null;

                        SetupTrayIcon();
                        LaunchEdgeAppMode();
                    });
                }
            });

            pollThread.IsBackground = true;
            pollThread.Start();

            _splashForm.Show();
            Application.Run(_appContext);
        }

        private static string ResolvePythonPath(string baseDir)
        {
            // 1. Портативный Python
            string portable = Path.Combine(baseDir, @"runtime\python.exe");
            if (File.Exists(portable)) return portable;

            // 2. Локальный .venv
            string venv = Path.Combine(baseDir, @".venv\Scripts\python.exe");
            if (File.Exists(venv)) return venv;

            // 3. Системный Python в PATH
            string pathEnv = Environment.GetEnvironmentVariable("PATH");
            if (!string.IsNullOrEmpty(pathEnv))
            {
                string[] parts = pathEnv.Split(';');
                foreach (string rawDir in parts)
                {
                    string dir = rawDir.Trim();
                    if (string.IsNullOrEmpty(dir)) continue;

                    // Пропускаем заглушки WindowsApps
                    if (dir.IndexOf("WindowsApps", StringComparison.OrdinalIgnoreCase) >= 0)
                        continue;

                    try
                    {
                        string candidate = Path.Combine(dir, "python.exe");
                        if (File.Exists(candidate))
                        {
                            return candidate;
                        }
                    }
                    catch { }
                }
            }

            return null;
        }

        private static bool WaitForServer(string url, int timeoutMs, int intervalMs)
        {
            int elapsed = 0;
            while (elapsed < timeoutMs)
            {
                if (_isExiting) return false;

                // Проверяем, не упал ли Python
                if (_pythonProcess != null && _pythonProcess.HasExited)
                {
                    return false;
                }

                try
                {
                    HttpWebRequest request = (HttpWebRequest)WebRequest.Create(url);
                    request.Timeout = 1000;
                    request.Method = "GET";
                    using (HttpWebResponse response = (HttpWebResponse)request.GetResponse())
                    {
                        int code = (int)response.StatusCode;
                        if (code >= 200 && code < 400)
                        {
                            return true;
                        }
                    }
                }
                catch
                {
                    // Сервер еще запускается
                }

                Thread.Sleep(intervalMs);
                elapsed += intervalMs;
            }

            return false;
        }

        private static void LaunchEdgeAppMode()
        {
            string edgePath = FindEdgeExecutable();
            string targetUrl = "http://127.0.0.1:7860";

            if (!string.IsNullOrEmpty(edgePath))
            {
                try
                {
                    string args = string.Format("--app=\"{0}\" --window-size=1280,860", targetUrl);
                    ProcessStartInfo psi = new ProcessStartInfo(edgePath, args)
                    {
                        UseShellExecute = false
                    };

                    _edgeProcess = Process.Start(psi);

                    DateTime startTime = DateTime.Now;

                    // Фоновый поток отслеживания жизненного цикла окна Edge
                    Thread waitThread = new Thread(delegate()
                    {
                        try
                        {
                            if (_edgeProcess != null)
                            {
                                _edgeProcess.WaitForExit();
                                TimeSpan lifetime = DateTime.Now - startTime;

                                // Если процесс окна жил более 2.5 сек и был закрыт — пользователь завершил работу
                                if (lifetime.TotalSeconds >= 2.5)
                                {
                                    TerminateAll();
                                    return;
                                }
                            }
                        }
                        catch { }

                        // Если Edge сразу форкнулся в существующий инстанс (lifetime < 2.5 с),
                        // информируем пользователя в трее о фоновой работе
                        try
                        {
                            if (_trayIcon != null)
                            {
                                _trayIcon.ShowBalloonTip(
                                    3500,
                                    "VoiceGuard активен",
                                    "Окно открыто в Microsoft Edge. Для остановки используйте значок в трее.",
                                    ToolTipIcon.Info
                                );
                            }
                        }
                        catch { }
                    });

                    waitThread.IsBackground = true;
                    waitThread.Start();
                    return;
                }
                catch
                {
                    // Fallback
                }
            }

            // Fallback на системный браузер по умолчанию
            try
            {
                Process.Start(targetUrl);
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    "Не удалось открыть браузер автоматически. Перейдите по адресу: " + targetUrl + "\n\n" + ex.Message,
                    "VoiceGuard",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Information
                );
            }
        }

        private static string FindEdgeExecutable()
        {
            string[] searchDirs = new string[]
            {
                Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),
                Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86),
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData)
            };

            foreach (string dir in searchDirs)
            {
                if (string.IsNullOrEmpty(dir)) continue;
                string edge = Path.Combine(dir, @"Microsoft\Edge\Application\msedge.exe");
                if (File.Exists(edge))
                {
                    return edge;
                }
            }

            return null;
        }

        private static void SetupTrayIcon()
        {
            try
            {
                _trayIcon = new NotifyIcon();

                Icon extracted = null;
                try
                {
                    extracted = Icon.ExtractAssociatedIcon(Application.ExecutablePath);
                }
                catch { }

                _trayIcon.Icon = extracted ?? SystemIcons.Shield;
                _trayIcon.Text = "VoiceGuard — AI Voice Detector (127.0.0.1:7860)";
                _trayIcon.Visible = true;

                ContextMenu menu = new ContextMenu();

                MenuItem titleItem = new MenuItem("VoiceGuard AI Detector");
                titleItem.Enabled = false;
                menu.MenuItems.Add(titleItem);

                menu.MenuItems.Add("-");

                MenuItem openItem = new MenuItem("Открыть интерфейс в браузере", delegate
                {
                    try { Process.Start("http://127.0.0.1:7860"); } catch { }
                });
                menu.MenuItems.Add(openItem);

                menu.MenuItems.Add("-");

                MenuItem exitItem = new MenuItem("Остановить и выйти", delegate
                {
                    TerminateAll();
                });
                menu.MenuItems.Add(exitItem);

                _trayIcon.ContextMenu = menu;
                _trayIcon.DoubleClick += delegate
                {
                    try { Process.Start("http://127.0.0.1:7860"); } catch { }
                };
            }
            catch { }
        }

        private static void OnProcessExit(object sender, EventArgs e)
        {
            TerminateAll();
        }

        public static void TerminateAll()
        {
            lock (_syncLock)
            {
                if (_isExiting) return;
                _isExiting = true;
            }

            try
            {
                if (_trayIcon != null)
                {
                    _trayIcon.Visible = false;
                    _trayIcon.Dispose();
                    _trayIcon = null;
                }
            }
            catch { }

            // Гасим дерево процессов Python через taskkill
            if (_pythonProcess != null)
            {
                try
                {
                    if (!_pythonProcess.HasExited)
                    {
                        ProcessStartInfo killPsi = new ProcessStartInfo("taskkill", string.Format("/F /T /PID {0}", _pythonProcess.Id))
                        {
                            CreateNoWindow = true,
                            UseShellExecute = false,
                            WindowStyle = ProcessWindowStyle.Hidden
                        };
                        using (Process kp = Process.Start(killPsi))
                        {
                            if (kp != null) kp.WaitForExit(3000);
                        }
                    }
                }
                catch { }

                try
                {
                    if (!_pythonProcess.HasExited)
                    {
                        _pythonProcess.Kill();
                    }
                }
                catch { }
            }

            try
            {
                if (_appContext != null)
                {
                    _appContext.ExitThread();
                }
            }
            catch { }

            try
            {
                Application.Exit();
            }
            catch { }

            try
            {
                Environment.Exit(0);
            }
            catch { }
        }
    }

    /// <summary>
    /// Премиальный Splash Screen в темной стилистике Frosted Glass
    /// </summary>
    internal class SplashForm : Form
    {
        public event EventHandler CancelRequested;

        private ProgressBar _progressBar;
        private Label _lblTitle;
        private Label _lblBadge;
        private Label _lblStatus;
        private Button _btnClose;
        private bool _dragging = false;
        private Point _dragCursorPoint;
        private Point _dragFormPoint;

        public SplashForm()
        {
            InitializeComponent();
        }

        private void InitializeComponent()
        {
            this.FormBorderStyle = FormBorderStyle.None;
            this.StartPosition = FormStartPosition.CenterScreen;
            this.Size = new Size(480, 240);
            this.BackColor = Color.FromArgb(13, 17, 23); // #0d1117 (VoiceGuard Dark)
            this.DoubleBuffered = true;
            this.ShowInTaskbar = true;
            this.TopMost = true;

            try
            {
                this.Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath);
            }
            catch { }

            // Кнопка отмены/закрытия в правом верхнем углу
            _btnClose = new Button
            {
                Text = "✕",
                FlatStyle = FlatStyle.Flat,
                ForeColor = Color.FromArgb(139, 148, 158),
                BackColor = Color.Transparent,
                Font = new Font("Segoe UI", 10F, FontStyle.Regular),
                Size = new Size(32, 28),
                Location = new Point(440, 8),
                Cursor = Cursors.Hand
            };
            _btnClose.FlatAppearance.BorderSize = 0;
            _btnClose.FlatAppearance.MouseOverBackColor = Color.FromArgb(33, 38, 45);
            _btnClose.Click += delegate
            {
                if (CancelRequested != null) CancelRequested(this, EventArgs.Empty);
                this.Close();
            };

            // Заголовок VoiceGuard
            _lblTitle = new Label
            {
                Text = "VoiceGuard",
                Font = new Font("Segoe UI", 22F, FontStyle.Bold),
                ForeColor = Color.FromArgb(240, 246, 252),
                BackColor = Color.Transparent,
                Location = new Point(36, 38),
                AutoSize = true
            };

            // Бейдж
            _lblBadge = new Label
            {
                Text = "AI Voice Deepfake Detection · Standalone Runner",
                Font = new Font("Segoe UI", 9F, FontStyle.Regular),
                ForeColor = Color.FromArgb(56, 189, 248), // #38bdf8 Neon Cyan
                BackColor = Color.Transparent,
                Location = new Point(38, 80),
                AutoSize = true
            };

            // Статус
            _lblStatus = new Label
            {
                Text = "Инициализация AI-детектора и запуск интерфейса...",
                Font = new Font("Segoe UI", 10F, FontStyle.Regular),
                ForeColor = Color.FromArgb(201, 209, 217),
                BackColor = Color.Transparent,
                Location = new Point(38, 136),
                AutoSize = true
            };

            // Прогресс-бар
            _progressBar = new ProgressBar
            {
                Style = ProgressBarStyle.Marquee,
                MarqueeAnimationSpeed = 25,
                Location = new Point(38, 172),
                Size = new Size(404, 6),
                ForeColor = Color.FromArgb(56, 189, 248)
            };

            this.Controls.Add(_btnClose);
            this.Controls.Add(_lblTitle);
            this.Controls.Add(_lblBadge);
            this.Controls.Add(_lblStatus);
            this.Controls.Add(_progressBar);

            // Перетаскивание формы мышкой
            this.MouseDown += OnMouseDown;
            this.MouseMove += OnMouseMove;
            this.MouseUp += OnMouseUp;
            _lblTitle.MouseDown += OnMouseDown;
            _lblTitle.MouseMove += OnMouseMove;
            _lblTitle.MouseUp += OnMouseUp;
        }

        private void OnMouseDown(object sender, MouseEventArgs e)
        {
            if (e.Button == MouseButtons.Left)
            {
                _dragging = true;
                _dragCursorPoint = Cursor.Position;
                _dragFormPoint = this.Location;
            }
        }

        private void OnMouseMove(object sender, MouseEventArgs e)
        {
            if (_dragging)
            {
                Point diff = Point.Subtract(Cursor.Position, new Size(_dragCursorPoint));
                this.Location = Point.Add(_dragFormPoint, new Size(diff));
            }
        }

        private void OnMouseUp(object sender, MouseEventArgs e)
        {
            _dragging = false;
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            base.OnPaint(e);
            Graphics g = e.Graphics;
            g.SmoothingMode = SmoothingMode.AntiAlias;

            // Тонкая внешняя неоновая рамка окна
            using (Pen borderPen = new Pen(Color.FromArgb(48, 54, 61), 1f))
            {
                g.DrawRectangle(borderPen, 0, 0, this.Width - 1, this.Height - 1);
            }

            // Акцентная светящаяся полоска сверху (Cyan Glow)
            using (LinearGradientBrush brush = new LinearGradientBrush(
                new Point(0, 0),
                new Point(this.Width, 0),
                Color.FromArgb(56, 189, 248),
                Color.FromArgb(99, 102, 241)))
            {
                g.FillRectangle(brush, 0, 0, this.Width, 3);
            }
        }
    }
}
