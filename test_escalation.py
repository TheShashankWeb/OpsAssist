from app.escalation import draft_escalation_email

result = draft_escalation_email(
    sector=None,
    recipient_name="Operations Manager",
    sender_name="Shash"
)

print("SUBJECT:", result["subject"])
print()
print("BODY:")
print(result["body"])
