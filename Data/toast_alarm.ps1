try {
  Import-Module BurntToast -ErrorAction Stop
} catch {
  try { Install-Module BurntToast -Scope CurrentUser -Force -AllowClobber -ErrorAction Stop } catch {}
  Import-Module BurntToast -ErrorAction Stop
}
$now = Get-Date
$parts = '11:48'.Split(':')
$h = [int]$parts[0]; $m = [int]$parts[1]
$dt = ($now.Date).AddHours($h).AddMinutes($m)
if ($dt -le $now) { $dt = $dt.AddDays(1) }

$t1 = New-BTText -Content 'Alarm'
$t2 = New-BTText -Content 'Alarm'
$bind = New-BTBinding -Children $t1,$t2
$vis  = New-BTVisual -BindingGeneric $bind
$aud  = New-BTAudio -Source 'ms-winsoundevent:Notification.Looping.Alarm2' -Loop
$act  = New-BTAction -SnoozeAndDismiss
$c    = New-BTContent -Visual $vis -Audio $aud -Actions $act -Scenario alarm

Submit-BTNotification -Content $c -Schedule -DeliveryTime $dt -UniqueIdentifier ('Jarvis-Alarm')