Run/test/deploy
---------------
Project uses poetry to manage itself
and its plugin poethepoet to run commands
so it's good to have 'em here:

```shell
> pip install poetry
> poetry self add 'poethepoet[poetry_plugin]'
> poetry install --with check --no-root
```

Some preset commands are available. Here are the list:

```shell
  buildrun - build image to run service     
  dockrun - run service in a docker single container
  pods - run service in k8s
  droppods - terminate k8s deployment       
  buildtest - build image to perform tests
  docktest - run tests in container
  buildqa - build image to analyze the code        
  dockqa - check code in container                 
  qa - perform code check locally
```

You can run these commands with:

```shell
poetry poe <command>
```
To run tests locally use:

```shell
poetry run pytest
```

Service can be configured via environment variables (or put in ".env" file). Here is the list with description:

```shell
TWO_FILES_BUFF_SIZE - the part of file in term of strings to keep in memory while reading
TWO_FILES_LOOKUP_DISTANCE - how far around we searching for a string pair
TWO_FILES_SIMILAR_THRESHOLD - koefficient of similarity used to find pair for the string in the second file  
TWO_FILES_OUTPUT_SEPARATOR - to separate different versions of strings
```

Task implementation
-------------------
- We should compare two files
- Find how are their lines changed from file to file
- If a pair remains the same we put only one copy in result
- If they differ not much we put the both copies on a single line
- If they differ a lot (couldn't find a pair) they are different string now and should take different rows in output

Considering we have no exact formal knowledge where should be positions of the same lines in two different versions of files
we use some artificial metric of similarity to compose the pairs of lines. This metric uses the algo known as “gestalt pattern matching”. It has quadratic time complexity though (qubic in the worst scenario)& So it comes with the price^ but it simply works.

In order not to keep all the files content in memory and not take too much time to find the similarity we look for a pair in the restricted range of line positions around the source line. First we try to find a pair at the same position. Then we look one position up and below in that order. Then two positions up and below and so on up to the defined limit. As soon as we find the match we stop looking, write the result for that string and proceed to the next one. The one we found won't be used in the further search, so the first pair to be found wins in order described..

Output format
-------------

Every pair found takes one line in the output file. If their differ from each other - they are divided with separator.
In case a pair was not found we put the only version of line and set the separator on the corresponding side to designate a midding part

Example of output file:
```shell
This line happens to occure in both files
version one=>version two
no match in the second file=>
=>no match in the first file
```

Service implementation
----------------------

Utility is implemented as a web service. You can process the two files using its API. In general one can use the following order of operations to process the files and get the result:
```shell
register -> to recieve a session id for uploading a pair of files
upload 1st file using session id -> system would be prepared to upload the first file
upload 2nd file using the same session id -> upload and processing of the both files is started
status -> get current state of operation or recive an url to download the result file
delete -> forget the session
```
There is no persistent storage for data and abstraction except for result file. Input files are read into memory chunk by chunk and are never stored on disk.
API description is available via call to "/" root path of the service. For example you can open this link in browser to see the autodoc of the API
```shell
localhost:8080/
```
There is a postman collection available in the JSON format as well, You can find it in the source code in 'test/request' directory
