// Code adapted from basic serial input tutorial on Arduino forums for the 
// PLD laser brain control project by Ian Brummel
// 06 Aug 2019

// Example 5 - Receive with start- and end-markers combined with parsing
// https://forum.arduino.cc/index.php?topic=396450.0 

// Vars here copied to brainStepperControl.ino
void recCommand() {
    static boolean recvInProgress = false;
    static byte idx = 0;
    char startMarker = '<';
    char endMarker = '>';
    char rc;

    while (Serial.available() > 0 && newData == false) {
        rc = Serial.read();

        if (recvInProgress == true) {
            if (rc != endMarker) {
                inCommandChars[idx] = rc;
                idx++;
                if (idx >= numChars) {
                    idx = numChars - 1;
                }
            }
            else {
                inCommandChars[idx] = '\0'; // terminate the string
                recvInProgress = false;
                idx = 0;
                newData = true;
            }
        }

        else if (rc == startMarker) {
            recvInProgress = true;
        }
    }
    if (newData == true) {
      strcpy(tempChars, inCommandChars); // Preserves integrity of received command
    }
}

void parseData() {      // split the data into its parts

    char * strtokIdx;                       // this is used by strtok() as an index
    
    strtokIdx = strtok(tempChars,",");      // get axis for the command to modify
    inCommandAxis = *strtokIdx;              // s=substrate, t=targets, p=pin, c=serial forward; NOTE: Need to copy the pointer to the variable. direct assignment breaks things
    
    strtokIdx = strtok(NULL, ",");          // get the modification type
    if (inCommandAxis == 'o' || inCommandAxis == 'i') {               // branch to set the data type based on command axis
        inCommandPinNum = atoi(strtokIdx);   // set the number for the pin to modify
    }
    else if (inCommandAxis == 'f') {
        //for(int i=2; i<strlen(inCommandChars); i++) {
          //inCommandSerForward[i-2] = inCommandChars[i];
        //}
        strcpy(inCommandSerForward, strtokIdx);
    }
    else if (inCommandAxis == 's' || inCommandAxis == 't' || inCommandAxis == 'l')
    {                                        // otherwise the second value should be a char signifying optype
        inCommandType = *strtokIdx;          // u=update, h=halt; NOTE: Need to copy the pointer to the variable. direct assignment breaks things
    }
    
    strtokIdx = strtok(NULL, ",");          // get next token, will be char or 
    inCommandParam = *strtokIdx;             // d=direction, g=goal position, a=acceleration, m=maxspeed,
                                            // w=write pin, c=clear pin

    if (inCommandType == 'u') {               // if the command is a parameter update
        strtokIdx = strtok(NULL, ",");      // Get next token from strtok
        if (inCommandParam == 'd' || inCommandParam == 'g' || inCommandParam == 'r') {
                inCommandValInt = atoi(strtokIdx);       // Convert direction or goal to int
        }
        else if (inCommandParam == 'a' || inCommandParam == 'm' || inCommandParam == 'v') {
                inCommandValFloat = atof(strtokIdx);       // Convert acceleration or max speed to float
        }
    }
}

void clearAxisModVars () {
    inCommandAxis = 'z';
    inCommandType = 'z';
    inCommandPinNum = -1;
    inCommandSerForward[numChars] = {0};
    inCommandParam = 'z';
    inCommandValInt = 0;  // This probably needs to not be 0... but will have to look for a vlaue that makes life easy
    inCommandValFloat = 0.0;
}

void showParsedData() {
    Serial.print("Command axis: ");
    Serial.println(inCommandAxis);
    
    if (inCommandAxis == 'c') {
        Serial.print("Command to forward: ");
        Serial.println(inCommandSerForward);
    }
    else if (inCommandAxis == 'o' || inCommandAxis == 'i') {
        Serial.print("Pin number: ");
        Serial.println(inCommandPinNum);
        Serial.print("Pin Write: ");
        Serial.println(inCommandParam);
    }
    else {
        Serial.print("Command Type: ");
        Serial.println(inCommandType);
        Serial.print("Command Parameter: ");
        Serial.println(inCommandParam);
        Serial.print("Command value: ");
        if (inCommandParam == 'd' || inCommandParam == 'g') {
                Serial.println(inCommandValInt);       // Print direction or goal as int
        }
        else if (inCommandParam == 'a' || inCommandParam == 'm' || inCommandParam == 'v') {
                Serial.println(inCommandValFloat);       // Print acceleration or max speed as float
        }
    }
    Serial.println("*****End Command*****");
}

void easyShowParsedData() {
    Serial.print("Command Axis: ");
    Serial.println(inCommandAxis);
    Serial.print("Serial Forward: ");
    Serial.println(inCommandSerForward);
    Serial.print("Pin Number: ");
    Serial.println(inCommandPinNum);
    Serial.print("Command Parameter: ");
    Serial.println(inCommandParam);
    Serial.print("Command Val Int: ");
    Serial.println(inCommandValInt);
    Serial.print("Command Val Float: ");
    Serial.println(inCommandValFloat);
    Serial.println("---------------");
}
