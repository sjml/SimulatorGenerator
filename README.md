SimulatorGenerator
==================

Inspired by [John Walker's review of Woodcutter Simulator](http://www.rockpapershotgun.com/2014/01/07/john-vs-the-trees-woodcutter-simulator-2013/), this bot procedurally generates box art for hot new games in the growing Job Simulator genre.

![Restaurant](http://shaneliesegang.com/tmp/restaurant-sim.png "Restaurant")
![Wizard](http://shaneliesegang.com/tmp/wizard-sim.png "Wizard")
![Pizza](http://shaneliesegang.com/tmp/pizza-sim.png "Pizza")

Twitter
-------
You can see it in action [on twitter](http://twitter.com/SimGenerator). 

It can also take requests! Tweet at it using the phrase "make one about" and it will respond back within a couple minutes. (NOTE: sometimes Twitter gets angry at it, so it doesn't consistently fulfill requests.)

* "@SimGenerator Make one about Ron Paul, please." 
* "Hey, @SimGenerator, make one about a sweet ninja." 
* _Et cetera_. 

It won't respond to any requests featuring words from [Darius Kazemi's word filter](https://github.com/dariusk/wordfilter). It also makes some rudimentary efforts to avoid shock images and jokes that I've seen too much. 

If something goes wrong, it just silently ignores the request. Alas. Tweet [@OptimistPanda](http://twitter.com/OptimistPanda) if you think it's broken. 


Local
-----
Alternately, you can invoke it locally and directly by running the `SimulatorGeneratorImage.py` through Python. (You'll need to have the [Python Requests](http://docs.python-requests.org/en/latest/) library installed, as well as [ImageMagick](http://imagemagick.org/).) You'll also need to track down a copy of Helvetica Ultra Compressed, which we can't freely distribute. 

### Instructions for Mac (assuming [Homebrew](http://brew.sh/)):

	~ $ brew install imagemagick
	~ $ sudo pip install requests
	~ $ git clone https://github.com/sjml/SimulatorGenerator.git
	~ $ cd SimulatorGenerator
	~/SimulatorGenerator $ ./SimulatorGeneratorImage.py \
		--output-file wizard-sim-boxart.png \
		--font-file helvetica-ultra-compressed.ttf \
		wizard
	~/SimulatorGenerator $ open wizard-sim-boxart.png

### Instructions for Ubuntu; other Linux distributions should be similar:

	~ $ sudo apt-get install imagemagick
	~ $ sudo pip install requests
	~ $ git clone https://github.com/sjml/SimulatorGenerator.git
	~ $ cd SimulatorGenerator
	~/SimulatorGenerator $ ./SimulatorGeneratorImage.py \
		--output-file wizard-sim-boxart.png \
		--font-file helvetica-ultra-compressed.ttf \
		wizard
	~/SimulatorGenerator $ eog wizard-sim-boxart.png

### Instructions for Windows:

1. [Install ImageMagick](http://www.imagemagick.org/script/binary-releases.php#windows). 
2. [Install Python](http://docs.python-guide.org/en/latest/starting/install/win/). Make sure you're installing version 2.7 of Python, NOT version 3. Follow that page's instructions for installing pip as well. 
3. Download the zip of [this repository](https://github.com/sjml/SimulatorGenerator). Unzip it.
4. Open a command prompt. 

In there:

	C:\Users\Albus\Downloads\SimulatorGenerator> python SimulatorGeneratorImage.py ^
		--output-file wizard-sim-boxart.png ^
		--font-file helvetica-ultra-compressed.ttf ^
		wizard
	C:\Users\Albus\Downloads\SimulatorGenerator> wizard-sim-boxart.png

### Usage
Run `python ./SimulatorGeneratorImage.py --help` for additional flags you can pass it. 