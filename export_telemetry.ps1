# Read-only export of existing Sysmon events during a completed run's time window.
# Does not install Sysmon, change its configuration, clear logs or invent events.
param(
    [Parameter(Mandatory=$true)][string]$RunDirectory
)
$ErrorActionPreference = 'Stop'
$runFolder = (Resolve-Path -LiteralPath $RunDirectory).Path
$auditRecords = @(Get-Content -LiteralPath (Join-Path $runFolder 'audit.jsonl') |
    ForEach-Object { $_ | ConvertFrom-Json })
if ($auditRecords.Count -lt 2) { throw 'Audit log is incomplete.' }
$first = $auditRecords[0]
$last = $auditRecords[-1]
if ($first.event -ne 'run_started' -or $last.event -ne 'run_finished') {
    throw 'A complete run with start and finish records is required.'
}
if ($first.mode -ne 'live') { throw 'This exporter requires a live run.' }
$start = [DateTimeOffset]::Parse($first.timestamp_utc).UtcDateTime.AddSeconds(-2)
$end = [DateTimeOffset]::Parse($last.timestamp_utc).UtcDateTime.AddSeconds(2)
$target = Join-Path $runFolder 'sysmon-events.xml'
# Check channel access before creating an output file.
$null = Get-WinEvent -ListLog 'Microsoft-Windows-Sysmon/Operational'
$filter = @{
    LogName = 'Microsoft-Windows-Sysmon/Operational'
    StartTime = $start
    EndTime = $end
    Id = @(1, 3, 5, 11)
}
try {
    $events = @(Get-WinEvent -FilterHashtable $filter -Oldest)
} catch {
    if ($_.FullyQualifiedErrorId -like 'NoMatchingEventsFound*') {
        $events = @()
    } else { throw }
}
# CreateNew refuses to overwrite an existing export.
$stream = [System.IO.File]::Open($target, [System.IO.FileMode]::CreateNew)
$writer = [System.IO.StreamWriter]::new($stream, [System.Text.UTF8Encoding]::new($false))
try {
    $writer.WriteLine('<Events>')
    foreach ($event in $events) { $writer.WriteLine($event.ToXml()) }
    $writer.WriteLine('</Events>')
} finally {
    $writer.Dispose()
}
Write-Output "Exported $($events.Count) existing events to $target"
Write-Output 'This includes other activity in the time window. Correlate PIDs, image paths, timestamps and ProcessGuid; do not attribute every event to this run.'
