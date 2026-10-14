thing = 1
thing_2 = 2
item = 3

testing = {
    thing : 'Thing',
    thing_2 : 'Thing 2',
    item : 'Item'
}

for goog in testing:
    print(testing[goog])
    
while True:
    user_input = input('Which one? ').capitalize()
    if user_input in testing.values():
        print("yes")