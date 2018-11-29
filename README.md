# README 

Pipeline to compile typescript definition files and 
applying 'hot-fixes' to make the most basic 
features work. 

## Usage

First install dependencies (OL-Souce and typescript)

~~~
npm install 
~~~ 

Then run the main script.

~~~
bash generate-types.sh
~~~

This will copy all openlayers source files to `@types/ol`, 
rename them to `.ts`-files and compile them (with lots of errors,
which can be ignored) 
while emitting declaration files.
In a second step those files are post-processed to 
have at least some type-checking, interfaces etc.

## Testing 

~~~
find ./@types/ol/ -name "*d.ts" -print0 | xargs -0 tsc 
~~~

## TODO

The comments before functions should be parsed and be used 
to provide type-information

