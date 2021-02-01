def calcCRC(message: str, split=True, debug=False):
          byteMsg = message.encode('ascii')
          length = 1 + byteMsg[1] - 34
          if debug:
            print(byteMsg, type(byteMsg))
            print("Message length: ", length)
          if length > 0:
              crc = 0x3fff
              for i in range(1, length + 1):
                  if debug:
                    print(i, byteMsg[i])
                  crc = crc ^ byteMsg[i]
                  for j in range(0, 8):
                      tmpCRC = crc
                      crc = crc >> 1
                      if tmpCRC & 0x1 == 1:
                          crc = crc ^ 0x2001
          crc = crc & 0x3fff
          if not split:
            return crc
          else:
            crc1 = int((crc & 0x7F) + 34)
            crc2 = int(((crc >> 7) & 0x7F) + 34)
            return {'CRC1': crc1, 'CRC2': crc2}

def genMsgString(command: str):
         sync = '!'
         length = len(command) + 34
         lenChar = chr(length)
         message = sync + lenChar + command
         crc = calcCRC(message)
         message = bytearray(message.encode('ascii'))
         message.append(crc['CRC1'])
         message.append(crc['CRC2'])
         
         return message

# Serial port 1 is /dev/ttyAMA0 --> SQM is connected here.