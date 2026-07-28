import uuid
import random

UUIDString = str 
def create_id()->UUIDString:
    return str(uuid.uuid4())

def create_number_id():
    return random.randint(1000000000, 9999999999)