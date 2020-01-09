import time

print('Hello, World!')

time.sleep(1.6)

print('My job is to count to 1,000 as quickly as possible.')
print(' ')

time.sleep(4)
print('Are you ready?')
print(' ')
time.sleep(1.6)
print('Then here I go!')
print(' ')
time.sleep(1)
print('In 3,')
time.sleep(1)
print('2,')
time.sleep(1)
print('1,')
time.sleep(1)
print('Start!!')

start, end = 0, 1000
for num in range(1,1000 + 1):
    if num <= 1000:
        print(num, end = " ")
       
print('Done!')
