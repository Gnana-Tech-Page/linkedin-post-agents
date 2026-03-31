import json
from datetime import datetime

state = json.load(open('state/pipeline_state.json'))
now = datetime.now()
print(f'Current time: {now.isoformat()}')
print()
print(f'{"Day":<6} {"Status":<10} {"Scheduled Time":<26} {"Due Now?":<10} {"Post ID"}')
print('-' * 75)

for item in state['schedule'][:10]:
    day        = item['day']
    posted     = item.get('posted', False)
    sched_time = item['scheduled_time']
    post_id    = item.get('post_id') or '-'
    due        = datetime.fromisoformat(sched_time) <= now
    status     = 'POSTED' if posted else ('DUE NOW' if due else 'pending')
    print(f'{day:<6} {status:<10} {sched_time:<26} {str(due):<10} {post_id}')