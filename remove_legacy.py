import os

path = r'c:\Users\pc\OneDrive\Desktop\nutritrack\backend\App.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# The functions to delete are between these bounds based on the previous view:
# 8694: @app.route('/api/auth/disabled_send-otp', methods=['POST'])
# 8856: 
# Let's delete lines 8694 to 8856 (0-indexed, so 8693 to 8856)

del lines[8693:8856]

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(lines)
    
print("Deleted legacy functions successfully!")
