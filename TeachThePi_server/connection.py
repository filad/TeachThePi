import logging
import socket
import threading
import sys
from multi_socket_output import *
from settings import *
from image import *
from video import *

RECEIVE_SIZE = 1024

# handles a command connection
class Connection (threading.Thread):
    
    def __init__(self, name, conn, camera, output, NN):
        threading.Thread.__init__(self)
        self.name = name
        self.command_socket = conn
        self.camera = camera
        self.output = output
        
        self.NN = NN
        
        self.video_socket = None
        self.video = None
        self.video_port = 0
        self.image = None
        self.image_port = 0
        
        
        
        self.logger = logging.getLogger("camera")         
        
    def run(self):
        # read commands forever
        while True:
             
            # read a command from the client
            self.logger.info('waiting for a command')
            command_bytes = self.command_socket.recv(RECEIVE_SIZE)
            if not command_bytes:
                self.logger.info('socket closed')
                break
            command = command_bytes.decode('ascii')
            self.logger.info('command = ' + command)
            print('command = ' + command)
            
            # gets the name of this device
            if command == 'get_name':
                send_bytes = DEVICE_NAME.encode('ascii')
                self.command_socket.sendall(send_bytes)
                
            # gets the video and image parameters
            elif command == 'getVideoParams':
                params = "%d,%d,%d,%d" % (WIDTH, HEIGHT, FPS, BPS)
                send_bytes = params.encode('ascii')
                self.command_socket.sendall(send_bytes)
                
            # gets a port for video, spawns a thread to wait for a connection on that port
            elif command == 'getVideoPort':
                try:
                    # create a video connection if necessary
                    if not self.output.contains_connection(self.name):
                        # close any open socket
                        if self.video_socket is not None:
                            self.video_socket.close()

                        # create a socket and bind it to an available port
                        self.video_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.video_socket.bind(('', 0))
                        self.video_port = self.video_socket.getsockname()[1]
                        self.logger.info('video socket on port %d' % self.video_port)
                    
                        # start a new video thread
                        self.video = Video(self.name, self.video_socket, self.output)
                        self.video.start()
                    
                    # report the port number back to the client
                    send_bytes = str(self.video_port).encode('ascii')
                    self.command_socket.sendall(send_bytes)
                except socket.error as msg:
                    self.logger.error('Bind Error: ' + str(msg[0]) + ' - ' + msg[1])

                    
            elif command == 'trainingA_Start':
                try:
                    self.NN.recordingA.set()
                    
                except socket.error as msg:
                    self.logger.error('Bind Error: ' + str(msg[0]) + ' - ' + msg[1])  
            
            elif command == 'trainingA_Stop':
                try:
                    self.NN.recordingA.clear()
                    
                    framesNum = str(self.NN.recorded_frames_Green)
                    send_bytes = framesNum.encode('ascii')
                    self.command_socket.sendall(send_bytes)
                except socket.error as msg:
                    self.logger.error('Bind Error: ' + str(msg[0]) + ' - ' + msg[1])
                                  
            
            elif command == 'trainingB_Start':
                try:
                    self.NN.recordingB.set()
                except socket.error as msg:
                    self.logger.error('Bind Error: ' + str(msg[0]) + ' - ' + msg[1]) 

            elif command == 'trainingB_Stop':
                try:
                    self.NN.recordingB.clear()
                    
                    framesNum = str(self.NN.recorded_frames_Blue)
                    send_bytes = framesNum.encode('ascii')
                    self.command_socket.sendall(send_bytes)
                    
                except socket.error as msg:
                    self.logger.error('Bind Error: ' + str(msg[0]) + ' - ' + msg[1]) 
                    
            elif command == 'clearA':
                try:
                    self.NN.clearLogits("Green")
                    msg = "Data cleared (from class A)"
                    send_bytes = msg.encode('ascii')
                    self.command_socket.sendall(send_bytes)
                except socket.error as msg:
                    self.logger.error('Bind Error: ' + str(msg[0]) + ' - ' + msg[1]) 

            elif command == 'clearB':
                try:
                    self.NN.clearLogits("Blue")
                    msg = "Data cleared (from class B)"
                    send_bytes = msg.encode('ascii')
                    self.command_socket.sendall(send_bytes)
                except socket.error as msg:
                    self.logger.error('Bind Error: ' + str(msg[0]) + ' - ' + msg[1]) 
                    

        # close the connection
        if self.video_socket is not None:
            self.logger.info('close video socket ' + self.name)
            self.video_socket.close()
        if self.output.contains_connection(self.name):
            self.output.remove_connection(self.name)
        self.command_socket.close()
        self.logger.info('closed command connection with ' + self.name)
