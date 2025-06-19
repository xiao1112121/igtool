import re

# Read the file
with open('src/ui/account_management.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all QMetaObject.invokeMethod calls with emit
content = re.sub(
    r'QMetaObject\.invokeMethod\(self, "update_account_table", Qt\.QueuedConnection\)',
    'self.status_updated.emit(username, account["status"])',
    content
)

# Write back
with open('src/ui/account_management.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done replacing QMetaObject.invokeMethod with emit') 