using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices.WindowsRuntime;
using Windows.Foundation;
using Windows.Foundation.Collections;
using Windows.UI.Xaml;
using Windows.UI.Xaml.Controls;
using Windows.UI.Xaml.Controls.Primitives;
using Windows.UI.Xaml.Data;
using Windows.UI.Xaml.Input;
using Windows.UI.Xaml.Media;
using Windows.UI.Xaml.Navigation;
using Windows.Devices.Gpio;
using Windows.Devices.Enumeration;
using Windows.Devices.I2c;
using Windows.System.Threading;
using System.Threading.Tasks;
using Windows.Devices.SerialCommunication;
using Windows.Storage.Streams;

// The Blank Page item template is documented at https://go.microsoft.com/fwlink/?LinkId=402352&clcid=0x409

namespace App1
{
    /// <summary>
    /// An empty page that can be used on its own or navigated to within a Frame.
    /// </summary>
    public sealed partial class MainPage : Page
    {
        bool state = false;
        int currentPin = 1;
        GpioPin pinA;
        GpioPin pinD;

        List<int> sequence;
        int index = 0;

        SerialDevice SerialPort;

        Dictionary<int, GpioPin> pins = new Dictionary<int, GpioPin>();

        Dictionary<int, char> intToChar = new Dictionary<int, char>
        {
            {2, 'A'},
            {3, 'B'},
            {4, 'D'},
            {5, 'L'},
            {6, 'N'},
            {7, 'P'},
            {8, 'R'},
            {9, 'T'},
            {10, 'U'},
        };

        Dictionary<char, int> charToInt = new Dictionary<char, int>
        {
            {'A', 2},
            {'B', 3},
            {'D', 4},
            {'L', 5},
            {'N', 6},
            {'P', 7},
            {'R', 8},
            {'T', 9},
            {'U', 10},
        };

        public MainPage()
        {
            this.InitializeComponent();


            //this.RunLastSlice();

            //pinD.Write(GpioPinValue.Low);
            //pinD.Write(GpioPinValue.High);
            //StartSequence(new List<int> { 8, 8, 2 });

            InitSerial();

            StackPanel panel = new StackPanel();
            for (int i = 0; i < 11; i++)
            {
                try
                {
                    StackPanel pinPanel = new StackPanel();
                    pinPanel.Orientation = Orientation.Horizontal;

                    GpioPin g = GpioController.GetDefault().OpenPin(i);
                    g.SetDriveMode(GpioPinDriveMode.Output);
                    Task.Delay(500).Wait();
                    //g.Write(GpioPinValue.Low);
                    pins[i] = g;

                    TextBlock t = new TextBlock();
                    t.Text = $"Pin {i}, {intToChar[i]}";
                    pinPanel.Children.Add(t);

                    Button b = new Button();
                    b.Content = $"Pulse {i}";
                    b.Click += B_Click;
                    pinPanel.Children.Add(b);

                    Button onButton = new Button();
                    onButton.Content = $"On {i}";
                    onButton.Click += OnButton_Click; ;
                    pinPanel.Children.Add(onButton);

                    Button offButton = new Button();
                    offButton.Content = $"Off {i}";
                    offButton.Click += OffButton_Click; ;
                    pinPanel.Children.Add(offButton);

                    panel.Children.Add(pinPanel);

                } catch (Exception) { }
            }
            mainGrid.Children.Add(panel);
            
        }

        private int parseContent(Button button)
        {
            string s = (string)button.Content;
            return int.Parse(s.Split(' ')[1]);
        }

        private void OffButton_Click(object sender, RoutedEventArgs e)
        {
            Button b = (Button)sender;
            GpioPin g = pins[parseContent(b)];
            textBox1.Text += "Disabling GPIO " + b.Content.ToString() + "\r\n";
            g.Write(GpioPinValue.Low);
        }

        private void OnButton_Click(object sender, RoutedEventArgs e)
        {
            Button b = (Button)sender;
            GpioPin g = pins[parseContent(b)];
            textBox1.Text += "Enabling GPIO " + b.Content.ToString() + "\r\n";
            g.Write(GpioPinValue.High);
        }

        private void B_Click(object sender, RoutedEventArgs e)
        {
            Button b = (Button)sender;
            
            textBox1.Text += "Pulsing GPIO " + b.Content.ToString() + "\r\n";
            PulsePin(parseContent(b));
        }

        private void PulsePin(int num)
        {
            GpioPin g = pins[num];
            g.Write(GpioPinValue.Low);
            Task.Delay(200).Wait();
            g.Write(GpioPinValue.High);
        }

        public async void InitSerial()
        {
            string aqs = SerialDevice.GetDeviceSelector("UART0");                   /* Find the selector string for the serial device   */
            var dis = await DeviceInformation.FindAllAsync(aqs);                    /* Find the serial device with our selector string  */
            SerialPort = await SerialDevice.FromIdAsync(dis[0].Id);    /* Create an serial device with our selected device */

            /* Configure serial settings */
            SerialPort.WriteTimeout = TimeSpan.FromMilliseconds(1000);
            SerialPort.ReadTimeout = TimeSpan.FromMilliseconds(1000);
            SerialPort.BaudRate = 9600;                                             /* mini UART: only standard baudrates */
            SerialPort.Parity = SerialParity.None;                                  /* mini UART: no parities */
            SerialPort.StopBits = SerialStopBitCount.One;                           /* mini UART: 1 stop bit */
            SerialPort.DataBits = 8;
        }

        public async void ReadSerial()
        {
            try
            {
                /* Read data in from the serial port */
                const uint maxReadLength = 1024;
                DataReader dataReader = new DataReader(SerialPort.InputStream);
                uint bytesToRead = await dataReader.LoadAsync(maxReadLength);
                string rxBuffer = dataReader.ReadString(bytesToRead);

                textBox1.Text += rxBuffer + "\r\n";
            } catch (Exception e)
            {
                textBox1.Text += e.ToString() + "\r\n";
            }
        }


        public void StartSequence(List<int> seq)
        {
            sequence = seq;
            ThreadPoolTimer.CreatePeriodicTimer(HandleNextInSequence, TimeSpan.FromSeconds(1));
        }

        public void HandleNextInSequence(ThreadPoolTimer t)
        {
            if (index >= sequence.Count)
            {
                t.Cancel();
                return;
            }

            int gpioNum = sequence[index];
            if (!pins.ContainsKey(gpioNum))
            {
                pins[gpioNum] = GpioController.GetDefault().OpenPin(gpioNum);
                pins[gpioNum].SetDriveMode(GpioPinDriveMode.Output);
            }
            textBox1.Text += $"Pulsing pin {gpioNum}.\r\n";
            pins[gpioNum].Write(GpioPinValue.High);
            pins[gpioNum].Write(GpioPinValue.Low);
            Task.Delay(200).Wait();
            pins[gpioNum].Write(GpioPinValue.High);

            index++;
        }

        public void ToggleLed(ThreadPoolTimer t)
        {
            state = !state;   
            pinA.Write(state ? GpioPinValue.High : GpioPinValue.Low);
        }

        public void SetNextLedHigh(ThreadPoolTimer t)
        {
            int i = currentPin;
            try
            {
                pinA = GpioController.GetDefault().OpenPin(i);
                pinA.SetDriveMode(GpioPinDriveMode.Output);
                pinA.Write(GpioPinValue.High);
                textBox1.Text += $"{i} {pinA.Read()}\r\n";
                pinA.Dispose();
            }
            catch (Exception)
            {
                textBox1.Text += $"{i} failed\r\n";
            }
            finally
            {
                currentPin += 1;
            }
        }

        public void RunLastSlice()
        {
            
            for (int i = 1; i < 40; i++)
            {
                try
                {
                    GpioPin g = GpioController.GetDefault().OpenPin(i);
                    g.SetDriveMode(GpioPinDriveMode.Output);
                    g.Write(GpioPinValue.Low);
                    textBox1.Text += i.ToString() + " " + (g.Read()).ToString() + "\r\n";
                    g.Dispose();
                    //System.Threading.Tasks.Task.Delay(1000).Wait();
                }
                catch (Exception e)
                {
                    textBox1.Text += i.ToString() + $" failed: {e}\r\n";
                }
            }
            
        }

        private void Button_Click(object sender, RoutedEventArgs e)
        {
            this.ReadSerial();
        }

        private void Button_Click_1(object sender, RoutedEventArgs e)
        {
            foreach (var pin in pins)
            {
                textBox1.Text += $"Pin {pin.Key}: {pin.Value.Read()}\r\n"; 
            }
        }

        private void Button_Click_2(object sender, RoutedEventArgs e)
        {
            textBox1.Text = "";
        }

        private void Button_Click_3(object sender, RoutedEventArgs e)
        {
            string seq = "rrrd ddlldddddr luuuuuurrrrrrrrrr ddllldrrrrr";
            textBox1.Text += "Sending sequence: ";
            foreach (char c in seq)
            {
                textBox1.Text += c;
                if (c == ' ')
                {
                    Task.Delay(3000).Wait();
                    continue;
                }
                PulsePin(charToInt[char.ToUpper(c)]);
                Task.Delay(500).Wait();
            }
            textBox1.Text += "\r\n";
        }
    }
}
