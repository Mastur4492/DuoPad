using System;
using System.Diagnostics;
using System.IO;
using System.Collections.Generic;
using System.Windows.Forms;
using Microsoft.Win32;

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

                // If running from desktop or parent directory, resolve relative script path
                if (!File.Exists(hubScript))
                {
                    string subDirScript = Path.Combine(appDir, "duopad", "duopad_hub.py");
                    if (File.Exists(subDirScript))
                    {
                        appDir = Path.Combine(appDir, "duopad");
                        hubScript = subDirScript;
                    }
                    else
                    {
                        string parentScript = Path.Combine(Directory.GetParent(appDir).FullName, "duopad_hub.py");
                        if (File.Exists(parentScript))
                        {
                            appDir = Directory.GetParent(appDir).FullName;
                            hubScript = parentScript;
                        }
                    }
                }

                if (!File.Exists(hubScript))
                {
                    MessageBox.Show(
                        "DuoPad Hub script (duopad_hub.py) could not be located in:\n" + appDir,
                        "DuoPad Launcher Error",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Error
                    );
                    return;
                }

                string pythonExe = LocatePythonExecutable(appDir);
                if (string.IsNullOrEmpty(pythonExe))
                {
                    DialogResult res = MessageBox.Show(
                        "Python 3.10+ was not found on your system.\n\n" +
                        "DuoPad requires Python 3 to run the low-latency gamepad server.\n" +
                        "Would you like to open the official Python download page?",
                        "Python Required - DuoPad",
                        MessageBoxButtons.YesNo,
                        MessageBoxIcon.Information
                    );
                    if (res == DialogResult.Yes)
                    {
                        Process.Start("https://www.python.org/downloads/");
                    }
                    return;
                }

                ProcessStartInfo psi = new ProcessStartInfo();
                psi.FileName = pythonExe;
                psi.Arguments = "\"" + hubScript + "\"";
                psi.WorkingDirectory = appDir;
                psi.UseShellExecute = false;
                psi.CreateNoWindow = true;

                Process.Start(psi);
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    "Failed to launch DuoPad Hub:\n\n" + ex.Message,
                    "DuoPad Startup Error",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
            }
        }

        static string LocatePythonExecutable(string appDir)
        {
            List<string> candidates = new List<string>();

            // 1. App-bundled Python or local virtual environments
            candidates.Add(Path.Combine(appDir, "pythonw.exe"));
            candidates.Add(Path.Combine(appDir, "venv", "Scripts", "pythonw.exe"));
            candidates.Add(Path.Combine(appDir, "env", "Scripts", "pythonw.exe"));
            candidates.Add(Path.Combine(appDir, ".venv", "Scripts", "pythonw.exe"));

            // 2. Windows User LocalAppData Python installations (Python 3.14, 3.13, 3.12, 3.11, 3.10)
            string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            if (!string.IsNullOrEmpty(localAppData))
            {
                // AppData\Local\Python\pythoncore-*
                string pyCoreDir = Path.Combine(localAppData, "Python");
                if (Directory.Exists(pyCoreDir))
                {
                    try
                    {
                        string[] subDirs = Directory.GetDirectories(pyCoreDir, "pythoncore*");
                        Array.Sort(subDirs);
                        Array.Reverse(subDirs); // Highest version first (e.g. 3.14)
                        foreach (string d in subDirs)
                        {
                            candidates.Add(Path.Combine(d, "pythonw.exe"));
                            candidates.Add(Path.Combine(d, "python.exe"));
                        }
                    }
                    catch { }
                }

                // AppData\Local\Programs\Python\Python3*
                string programsDir = Path.Combine(localAppData, "Programs", "Python");
                if (Directory.Exists(programsDir))
                {
                    try
                    {
                        string[] subDirs = Directory.GetDirectories(programsDir, "Python3*");
                        Array.Sort(subDirs);
                        Array.Reverse(subDirs);
                        foreach (string d in subDirs)
                        {
                            candidates.Add(Path.Combine(d, "pythonw.exe"));
                            candidates.Add(Path.Combine(d, "python.exe"));
                        }
                    }
                    catch { }
                }
            }

            // 3. System Program Files
            string programFiles = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles);
            if (!string.IsNullOrEmpty(programFiles))
            {
                try
                {
                    string[] pfDirs = Directory.GetDirectories(programFiles, "Python3*");
                    Array.Sort(pfDirs);
                    Array.Reverse(pfDirs);
                    foreach (string d in pfDirs)
                    {
                        candidates.Add(Path.Combine(d, "pythonw.exe"));
                        candidates.Add(Path.Combine(d, "python.exe"));
                    }
                }
                catch { }
            }

            // 4. Windows Registry Python Core Lookups
            AddRegistryPythons(Registry.CurrentUser, candidates);
            AddRegistryPythons(Registry.LocalMachine, candidates);

            // 5. Test each candidate for existence
            foreach (string path in candidates)
            {
                if (!string.IsNullOrEmpty(path) && File.Exists(path))
                {
                    return path;
                }
            }

            // 6. Fallback to system PATH binaries
            string[] pathBinaries = new string[] { "pythonw.exe", "py.exe", "python.exe" };
            foreach (string bin in pathBinaries)
            {
                if (IsBinaryOnPath(bin))
                {
                    return bin;
                }
            }

            return null;
        }

        static void AddRegistryPythons(RegistryKey root, List<string> candidates)
        {
            try
            {
                using (RegistryKey key = root.OpenSubKey(@"Software\Python\PythonCore"))
                {
                    if (key != null)
                    {
                        string[] versionNames = key.GetSubKeyNames();
                        Array.Sort(versionNames);
                        Array.Reverse(versionNames);
                        foreach (string ver in versionNames)
                        {
                            using (RegistryKey installKey = key.OpenSubKey(ver + @"\InstallPath"))
                            {
                                if (installKey != null)
                                {
                                    object val = installKey.GetValue("ExecutablePath");
                                    if (val != null)
                                    {
                                        string p = val.ToString();
                                        candidates.Add(p);
                                        string pw = Path.Combine(Path.GetDirectoryName(p), "pythonw.exe");
                                        candidates.Add(pw);
                                    }
                                    object dirVal = installKey.GetValue("");
                                    if (dirVal != null)
                                    {
                                        string dir = dirVal.ToString();
                                        candidates.Add(Path.Combine(dir, "pythonw.exe"));
                                        candidates.Add(Path.Combine(dir, "python.exe"));
                                    }
                                }
                            }
                        }
                    }
                }
            }
            catch { }
        }

        static bool IsBinaryOnPath(string binaryName)
        {
            string pathEnv = Environment.GetEnvironmentVariable("PATH");
            if (string.IsNullOrEmpty(pathEnv)) return false;

            string[] paths = pathEnv.Split(';');
            foreach (string p in paths)
            {
                try
                {
                    string full = Path.Combine(p.Trim(), binaryName);
                    if (File.Exists(full)) return true;
                }
                catch { }
            }
            return false;
        }
    }
}
