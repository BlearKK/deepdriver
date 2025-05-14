# gevent_monkey.py
# 在任何其他导入之前执行monkey patching
from gevent import monkey
monkey.patch_all()

print("Gevent monkey patching completed before any other imports")
