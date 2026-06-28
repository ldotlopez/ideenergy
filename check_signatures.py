from globalomnium import Client
import inspect

print('get_historical_consumption_range signature:')
print(inspect.signature(Client.get_historical_consumption_range))

print()
print('backfill_all_historical signature:')
print(inspect.signature(Client.backfill_all_historical))