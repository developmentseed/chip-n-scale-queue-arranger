## Lambda Examples
*(how to customize this repo for running your ML inference task)*

The primary functionality of this repository is contained in the lambda function located at `lambda/download_and_predict/handler.py`. It is intentionally very little code to allow for easy configuration: with the imports and assertions removed, there is one class instantiation and four method calls. The class `DownloadAndPredict` provides the base functionality required to run machine learning inference:
  - Creates a list of Mercator tiles based on an input SQS event.
  - Downloads those tiles from a TMS/XYS tile endpoint and puts them in the proper format for sending them to Tensorflow Serving or an equivalent Docker image.
  - Sends the payload to the prediction endpoint.
  - Saves the result into a database.

There are two primary options to customize this workflow:
  - Add new code to `handler.py` to manipulate the returned values (`tiles`, `payload`, `content`, etc.)
  - Subclass `DownloadAndPredict` to provide alternative methods for the operations listed above.

Any additional third-party libraries should be added to `lambda/setup.py` for inclusion in the lambda function deployment.

Examples of customization are listed in this library to show how `chip-n-scale-queue-arranger` can be used with a variety of different tools.

- [Download imagery from Sentinel Hub](sentinel_hub.py). For more information, check out the [`sentinelhub-py` docs](https://sentinelhub-py.readthedocs.io/en/latest/).
- [Download larger tiles and create smaller tiles for inference](super_tiles.py). This is useful for reducing the load on the imagery/tile endpoint.
- [Save results to `ml-enabler`](ml_enabler.py). For more information, check out the [`ml-enabler` repo](https://github.com/hotosm/ml-enabler).
