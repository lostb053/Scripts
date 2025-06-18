# Memory Monitor - Priority Alert System
# Monitors Private Bytes (RAM + Pagefile) and shows priority alerts

param(
    [int]$ThresholdGB = 3,
    [int]$CheckIntervalSeconds = 30,
    [switch]$RunOnce
)

# Add required assemblies
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Add Windows API for topmost window behavior
Add-Type @"
    using System;
    using System.Runtime.InteropServices;
    public class WinAPI {
        [DllImport("user32.dll")]
        public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);
        [DllImport("user32.dll")]
        public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
        [DllImport("user32.dll")]
        public static extern IntPtr GetForegroundWindow();
        [DllImport("user32.dll")]
        public static extern bool SetForegroundWindow(IntPtr hWnd);
        
        public static readonly IntPtr HWND_TOPMOST = new IntPtr(-1);
        public static readonly IntPtr HWND_NOTOPMOST = new IntPtr(-2);
        public const uint SWP_NOMOVE = 0x0002;
        public const uint SWP_NOSIZE = 0x0001;
        public const uint SWP_SHOWWINDOW = 0x0040;
        public const int SW_SHOW = 5;
    }
"@

# Function to create priority alert dialog
function Show-PriorityAlert {
    param(
        [string]$ProcessName,
        [int]$ProcessId,
        [string]$MemoryUsage,
        [System.Diagnostics.Process]$Process
    )
    
    $message = @"
HIGH MEMORY USAGE DETECTED!

Process: $ProcessName
PID: $ProcessId
Memory Usage: $MemoryUsage GB
Threshold: $ThresholdGB GB

This process is consuming excessive memory and may indicate a memory leak.
"@

    # Create form with priority settings
    $form = New-Object System.Windows.Forms.Form
    $form.Text = "MEMORY ALERT - $ProcessName"
    $form.Size = New-Object System.Drawing.Size(450, 320)
    $form.StartPosition = [System.Windows.Forms.FormStartPosition]::CenterScreen
    $form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::FixedDialog
    $form.MaximizeBox = $false
    $form.MinimizeBox = $false
    $form.TopMost = $true
    $form.ShowInTaskbar = $true
    $form.BackColor = [System.Drawing.Color]::FromArgb(255, 255, 240)
    
    # Warning icon and styling
    $form.Font = New-Object System.Drawing.Font("Segoe UI", 9)
    
    # Message label
    $label = New-Object System.Windows.Forms.Label
    $label.Text = $message
    $label.Size = New-Object System.Drawing.Size(420, 160)
    $label.Location = New-Object System.Drawing.Point(15, 15)
    $label.Font = New-Object System.Drawing.Font("Segoe UI", 9)
    $form.Controls.Add($label)
    
    # Process details
    try {
        $processInfo = "Path: $($Process.MainModule.FileName)`nStart Time: $($Process.StartTime)"
        $detailLabel = New-Object System.Windows.Forms.Label
        $detailLabel.Text = $processInfo
        $detailLabel.Size = New-Object System.Drawing.Size(420, 40)
        $detailLabel.Location = New-Object System.Drawing.Point(15, 180)
        $detailLabel.Font = New-Object System.Drawing.Font("Segoe UI", 8)
        $detailLabel.ForeColor = [System.Drawing.Color]::DarkBlue
        $form.Controls.Add($detailLabel)
    } catch {
        # Process might not have accessible details
    }
    
    # Terminate button
    $btnTerminate = New-Object System.Windows.Forms.Button
    $btnTerminate.Text = "Terminate Process"
    $btnTerminate.Location = New-Object System.Drawing.Point(50, 230)
    $btnTerminate.Size = New-Object System.Drawing.Size(140, 35)
    $btnTerminate.BackColor = [System.Drawing.Color]::FromArgb(255, 100, 100)
    $btnTerminate.ForeColor = [System.Drawing.Color]::White
    $btnTerminate.Font = New-Object System.Drawing.Font("Segoe UI", 9, [System.Drawing.FontStyle]::Bold)
    $btnTerminate.Add_Click({
        $result = [System.Windows.Forms.MessageBox]::Show(
            "Are you sure you want to terminate $ProcessName (PID: $ProcessId)?`n`nThis action cannot be undone.",
            "Confirm Termination",
            [System.Windows.Forms.MessageBoxButtons]::YesNo,
            [System.Windows.Forms.MessageBoxIcon]::Warning
        )
        
        if ($result -eq [System.Windows.Forms.DialogResult]::Yes) {
            try {
                Stop-Process -Id $ProcessId -Force -ErrorAction Stop
                [System.Windows.Forms.MessageBox]::Show(
                    "Process $ProcessName (PID: $ProcessId) has been terminated.",
                    "Process Terminated",
                    [System.Windows.Forms.MessageBoxButtons]::OK,
                    [System.Windows.Forms.MessageBoxIcon]::Information
                )
            } catch {
                [System.Windows.Forms.MessageBox]::Show(
                    "Failed to terminate process: $($_.Exception.Message)",
                    "Termination Failed",
                    [System.Windows.Forms.MessageBoxButtons]::OK,
                    [System.Windows.Forms.MessageBoxIcon]::Error
                )
            }
        }
        $form.Close()
    })
    $form.Controls.Add($btnTerminate)
    
    # Monitor button
    $btnMonitor = New-Object System.Windows.Forms.Button
    $btnMonitor.Text = "Open Task Manager"
    $btnMonitor.Location = New-Object System.Drawing.Point(200, 230)
    $btnMonitor.Size = New-Object System.Drawing.Size(140, 35)
    $btnMonitor.BackColor = [System.Drawing.Color]::FromArgb(70, 130, 180)
    $btnMonitor.ForeColor = [System.Drawing.Color]::White
    $btnMonitor.Add_Click({
        Start-Process "taskmgr.exe" -ArgumentList "/7" # Open to Processes tab
        $form.Close()
    })
    $form.Controls.Add($btnMonitor)
    
    # Dismiss button
    $btnDismiss = New-Object System.Windows.Forms.Button
    $btnDismiss.Text = "Dismiss"
    $btnDismiss.Location = New-Object System.Drawing.Point(350, 230)
    $btnDismiss.Size = New-Object System.Drawing.Size(80, 35)
    $btnDismiss.Add_Click({ $form.Close() })
    $form.Controls.Add($btnDismiss)
    
    # Force window to top and show
    $form.Add_Shown({
        $form.Activate()
        [WinAPI]::SetWindowPos($form.Handle, [WinAPI]::HWND_TOPMOST, 0, 0, 0, 0, 
            [WinAPI]::SWP_NOMOVE -bor [WinAPI]::SWP_NOSIZE -bor [WinAPI]::SWP_SHOWWINDOW)
        [WinAPI]::SetForegroundWindow($form.Handle)
        
        # Flash the window to get attention
        $form.WindowState = [System.Windows.Forms.FormWindowState]::Normal
        $form.BringToFront()
        $form.Focus()
    })
    
    # Auto-dismiss after 5 minutes to prevent accumulation
    $timer = New-Object System.Windows.Forms.Timer
    $timer.Interval = 300000 # 5 minutes
    $timer.Add_Tick({
        $timer.Stop()
        $form.Close()
    })
    $timer.Start()
    
    # Play system sound
    [System.Media.SystemSounds]::Exclamation.Play()
    
    # Show dialog
    $form.ShowDialog() | Out-Null
    $timer.Stop()
}

# Function to check memory usage
function Check-MemoryUsage {
    $thresholdBytes = $ThresholdGB * 1GB
    $alertedProcesses = @{}
    
    try {
        # Get processes with high memory usage (Private Bytes = RAM + Pagefile)
        $highMemoryProcesses = Get-Process | Where-Object {
            $_.PrivateMemorySize64 -gt $thresholdBytes -and 
            $_.ProcessName -notin @('System', 'Idle', 'Registry') -and
            $_.Id -ne $PID  # Don't alert on ourselves
        } | Sort-Object PrivateMemorySize64 -Descending
        
        foreach ($proc in $highMemoryProcesses) {
            $memInGB = [math]::Round(($proc.PrivateMemorySize64 / 1GB), 2)
            $processKey = "$($proc.ProcessName)-$($proc.Id)"
            
            # Only show alert if we haven't already alerted for this process in this session
            if (-not $alertedProcesses.ContainsKey($processKey)) {
                Write-Host "ALERT: High memory usage detected - $($proc.ProcessName) (PID: $($proc.Id)) - $memInGB GB" -ForegroundColor Red
                
                # Show priority alert
                Show-PriorityAlert -ProcessName $proc.ProcessName -ProcessId $proc.Id -MemoryUsage $memInGB -Process $proc
                
                # Mark as alerted
                $alertedProcesses[$processKey] = $true
            }
        }
        
        if ($highMemoryProcesses.Count -eq 0) {
            Write-Host "$(Get-Date -Format 'HH:mm:ss'): No high memory usage detected (threshold: $ThresholdGB GB)" -ForegroundColor Green
        }
        
    } catch {
        Write-Error "Error checking memory usage: $($_.Exception.Message)"
    }
}

# Main execution
Write-Host "Memory Monitor Started - Threshold: $ThresholdGB GB" -ForegroundColor Cyan
Write-Host "Monitoring Private Bytes (RAM + Pagefile usage)" -ForegroundColor Cyan

if ($RunOnce) {
    Write-Host "Running single check..." -ForegroundColor Yellow
    Check-MemoryUsage
} else {
    Write-Host "Continuous monitoring enabled - Check interval: $CheckIntervalSeconds seconds" -ForegroundColor Yellow
    Write-Host "Press Ctrl+C to stop monitoring" -ForegroundColor Yellow
    
    while ($true) {
        Check-MemoryUsage
        Start-Sleep -Seconds $CheckIntervalSeconds
    }
}