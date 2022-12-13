import threading
import time

class NN_Mock (threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.myEvent = threading.Event()
        self.myCount = 0

    def run(self):
        while (1):
            
            if (self.myEvent.isSet()):
                print("event is SET")
                self.myCount += 1
            else:
                print("event is not set")
            
            time.sleep(1)


def main():
    nn = NN_Mock()
    nn.start()
    
    #read any user input
    value = input()
    
    if value:
        nn.myEvent.set()
    
    
if __name__ == "__main__":
    main()
