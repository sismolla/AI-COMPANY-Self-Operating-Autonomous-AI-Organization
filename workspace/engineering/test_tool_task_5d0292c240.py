from tool import process_data
res = process_data({'test': 123})
assert res['processed'] is True
