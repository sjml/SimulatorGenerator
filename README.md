SimulatorGenerator
==================

Inspired by [John Walker's review of Woodcutter Simulator](http://www.rockpapershotgun.com/2014/01/07/john-vs-the-trees-woodcutter-simulator-2013/), this bot procedurally generates box art for hot new games in the growing Job Simulator genre.

You can either invoke it locally and directly by running the `SimulatorGeneratorImage.py` through Python. (You'll need to have the [Python Requests](http://docs.python-requests.org/en/latest/) library installed, as well as [ImageMagick](http://imagemagick.org/).)

Or, you can see it in action [on twitter](http://twitter.com/SimulatorGenerator). 

It can also take requests! Tweet at it using the phrase "make one about" and it will respond back within a couple minutes. (NOTE: sometimes Twitter gets angry at it, so it doesn't consistently fulfill requests.)

* "@SimGenerator Make one about Ron Paul, please." 
* "Hey, @SimGenerator, make one about a sweet ninja." 
* _Et cetera_. 

It won't respond to any requests featuring words from [Darius Kazemi's word filter](https://github.com/dariusk/wordfilter). It also makes some rudimentary efforts to avoid shock images and jokes that I've seen too much. 

If something goes wrong, it just silently ignores the request. Alas. Tweet [@OptimistPanda](http://twitter.com/OptimistPanda) if you think it's broken. 
