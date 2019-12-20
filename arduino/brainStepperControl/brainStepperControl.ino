#include <AccelStepper_50pctDuty.h>
#include <AccelStepper.h>
//NOTE: *.ino is included automatically by the Arduino compiler.

// Define the available stepper motors
// Note that pins are defined by the number after D or their Axx designations. i.e. A3 = A3 and D1 = 1
AccelStepper50pctDuty substrate(AccelStepper50pctDuty::DRIVER, 2, 3);
AccelStepper50pctDuty target(AccelStepper50pctDuty::DRIVER, 4, 5);
int rasterCenter = 0;   // Stores center position of target when raster is started
int rasterSteps = 0;    // Stores the number of steps across the target, set based on target size.
bool rasterOn = false;  // Sets the raster on off state
bool centering = false; // Set based on whether the target is returning to center
int rasterSide = 1;     // Which side of the target should be moved to

// Define the laser pulsing, using a stepper motor that just runs at constant speed
AccelStepper laser(AccelStepper::DRIVER, 12, A0);   // A0 is used as it is currently not connected to anything and we don't need a direction pin here.

//Define variables for serial input handling
const byte numChars = 32;
char inCommandChars[numChars];
char tempChars[numChars];        // temporary array for use when parsing

// variables to hold the parsed data
char inCommandAxis = 'z';
char inCommandType = 'z';
char inCommandPinNum = 0;

char inCommandSerForward[numChars];
char inCommandParam = 'z';
int inCommandValInt;
float inCommandValFloat;

boolean newData = false;

// Define other variables
bool commandReady = false;


/********************************************** Main run loops **********************************************/
void setup() {
    Serial.begin(115200);
    //Serial1.begin(9600);         // Baud rate will need to be adjusted to match the device that is connected in future
    
    // ** Set up motor limits and parameters ** //
    substrate.setMaxSpeed(4000);  // set the max substrate speed to 4rps
    target.setMaxSpeed(1000); // set max target speed as 1 rps PROB TOO FAST
    
    substrate.setMinPulseWidth(50000);

    substrate.setAcceleration(8000); // Probably going to stick with runSpeed for constant speeds since we have plenty of torque
    target.setAcceleration(2000); // set acceleration limits (using 2x max speed to start)   

    // May need to invert pins for the directions to match reality
    // substrate.setPinsInverted(directionInvert=true, stepInvert=false); 
    // target.setPinsInverted(directionInvert=true, stepInvert=false);

    // ** Set up laser limits and parameters ** //
    laser.setMaxSpeed(20);       // Don't want laser to run above 20 Hz
    laser.setMinPulseWidth(50);  // Laser requires a >=15 micrsecond pulse
    laser.setSpeed(5);

    // Set up pins as in or output
    setupPins();
}

void loop() {
    recCommand();                           // Check if there is a command to receive from the serial input
    if (newData == true) {
        parseData();                        // if there is new data parse it
        newData = false;                    // Clears the new data variable
        commandReady = true;                // Flags for setting pins or updating motor params
        easyShowParsedData();
        //Serial.println("commandReady=true.\nEntering switch-case...");
    }
    if (commandReady == true) {
      
        switch (inCommandAxis) {
            case 'o':
                digitalPinWrite();
                break;
            case 'i':
                Serial.println(digitalPinRead());
                break;
            case 'f':
                forwardSerial1();
                break;
            case 'r':
                readSerial1();
                break;
            case 's':
                updateMotorParams(substrate);
                break;
            case 't':
                updateMotorParams(target);
                break;
            case 'l':
                updateLaserParams(laser);
                break;
            default:
                commandReady = false; // Protect against errant commands sending the arduino into a loop
                break;
        }
    }
    
    // Handle rastering
    if (rasterSide == 0 && centering == false) {
      target.moveTo(rasterCenter);
      centering = true;
    }
    else if (rasterSide == 0 && centering == true){
      if (target.distanceToGo() == 0) {
        centering = false;
        rasterSide = 1;
      }
    }
    else if (rasterOn == true && target.distanceToGo() == 0) {
        rasterSide *= -1;   // Switch which direction to move
        target.moveTo(rasterCenter + (rasterSteps * rasterSide)); // Set the new goal position
    }
    
    
    // Set cross-board GPIO pins as needed
    if (target.isRunning()) {
        digitalWrite(19, HIGH);
    }
    else {
        digitalWrite(19, LOW);
    }
    if (substrate.isRunning()) {
        digitalWrite(18, HIGH);
    }
    else {
        digitalWrite(18, LOW);
    }
    if (laser.isRunning()) {
        digitalWrite(20, HIGH);
    }
    else {
        digitalWrite(20, LOW);
    }
    
    // Handle running the motors to their positions
    target.run();
    substrate.run();
    laser.runSpeed();
}
