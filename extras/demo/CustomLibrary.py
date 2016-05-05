import logging

class CustomLibrary:

    def custom_log(self, text):
        sample_array = [i*2 for i in xrange(100)]
        logging.info("Text: {}".format(text))
        logging.debug("Sample Array: {}".format(sample_array))