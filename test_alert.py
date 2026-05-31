from app.alert_engine import run_all_alerts

alerts = run_all_alerts()
print(f"Total alerts: {len(alerts)}")
print()
for a in alerts:
    print(f"[{a['type']}] {a['message'][:80]}")
    print()
