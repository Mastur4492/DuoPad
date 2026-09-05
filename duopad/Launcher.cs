using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

namespace DuoPadLauncher
{
    static class Program
    {
        [STAThread]
        static void Main()
        {
            try
            {
                string appDir = AppDomain.CurrentDomain.BaseDirectory.TrimEnd('\\');
                string hubScript = Path.Combine(appDir, "duopad_hub.py");

                // If running from Desktop shortcut where exe is elsewhere, ensure valid script path
                if (!File.Exists(hubScript))
                {
                    string defaultDir = @"C:\Users\mo.mastur\OneDrive\Desktop\console\duopad";
                    if (File.Exists(Path.Combine(defaultDir, "duopad_hub.py")))
                    {
                        appDir = defaultDir;
                        hubScript = Path.Combine(appDir, "duopad_hub.py");
                    }
                }

                // Locate Python executable
                string[] candidatePythons = new string[]
                {
                    Path.Combine(appDir, "pythonw.exe"),
                    Path.Combine(appDir, "venv", "Scripts", "pythonw.exe"),
                    @"C:\Users\mo.mastur\anaconda3\pythonw.exe",
                    @"C:\Users\mo.mastur\AppData\Local\Programs\Python\Python311\pythonw.exe",
                    @"C:\Users\mo.mastur\AppData\Local\Programs\Python\Python310\pythonw.exe",
                    @"C:\Users\mo.mastur\AppData\Local\Programs\Python\Python312\pythonw.exe",
                    "pythonw.exe"
                };

                string chosenPython = null;
                foreach (string candidate in candidatePythons)
                {
                    if (File.Exists(candidate))
                    {
                        chosenPython = candidate;
                        break;
                    }
                }

                if (chosenPython == null)
                {
                    chosenPython = "pythonw.exe";
                }

                ProcessStartInfo psi = new ProcessStartInfo();
                psi.FileName = chosenPython;
                psi.Arguments = "\"" + hubScript + "\"";
                psi.WorkingDirectory = appDir;
                psi.UseShellExecute = false;
                psi.CreateNoWindow = true;

                Process.Start(psi);
            }
            catch (Exception ex)
            {
                MessageBox.Show("Failed to launch DuoPad Hub:\n" + ex.Message, "DuoPad Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }
    }
}
