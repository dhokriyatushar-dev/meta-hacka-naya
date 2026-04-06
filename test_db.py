import os
import sys

def get_env_var(filepath, var_name):
    if not os.path.exists(filepath): return None
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith(var_name + '='):
                return line.split('=', 1)[1].strip().strip('\"\'')
    return None

url = get_env_var('frontend/.env.local', 'NEXT_PUBLIC_SUPABASE_URL')
key = get_env_var('frontend/.env.local', 'NEXT_PUBLIC_SUPABASE_ANON_KEY')

if not url or not key:
    print('Failed to find SUPABASE_URL or SUPABASE_ANON_KEY in frontend/.env.local')
    exit(1)

os.environ['SUPABASE_URL'] = url
os.environ['SUPABASE_KEY'] = key

sys.path.insert(0, os.path.abspath('backend'))
from db.supabase_client import _get_client

client = _get_client()
if not client:
    print('Failed to initialize client')
    exit(1)

def check_table(table_name):
    try:
        response = client.table(table_name).select('id').limit(1).execute()
        print(f'[SUCCESS] Table {table_name} is accessible.')
    except Exception as e:
        print(f'[ERROR] Table {table_name} error: {e}')

tables = ['students', 'student_quizzes', 'student_projects', 'student_roadmaps', 'roadmap_history', 'progress_snapshots']

print(f'\nChecking Supabase connection to: {url}...\n')
for table in tables:
    check_table(table)
print('\nDone.')
