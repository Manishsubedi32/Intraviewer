from slowapi import Limiter
from slowapi.util import get_remote_address
 
 #this file is to limit certain ip user to call the api certain times in a given tie
limiter = Limiter(key_func = get_remote_address)