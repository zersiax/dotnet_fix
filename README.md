# dotnet_fix
NVDA scratchpad script to fix various .NET UI annoyances
## What?

A script (not even an addon, I honestly don't have time to figure out what the process is for packaging, submitting and maintaining an NVDA addon right now) that tries its best to work around a number of annoyances that crop up in .NET-based user interfaces. Notably, it tries to:

- Fix unlabeled buttons and other elements by grabbing text that is inside the button but not properly associated with said button. This works surprisingly often.
- It TRIES, keyword TRIES, to figure out when NVDA is about to encounter a "superawesomeListItem.Subview.LineItem" type of element and grabs the text of the child nodes instead. This, again, works surprisingly often and it's honestly a travesty Microsoft hasn't fixed this themselves for the last 20 years, but what can you do.

## Why?

Because I got tired of seeing this fall over every single time I grab a random c#-based app off GitHub.

## How?

Enable the scratchpad directory in NVDA's Advanced Settings, then copy-paste this script into the relevant folder.

## What if it breaks?

You're on your own, I'm afraid. I scrobbled this together from various existing addons and barely know how it works myself, I just know it does from my testing. Feel free to let me know if it works or breaks for you but no guarantees it will work, or will continue to work when NVDA gets updated. This is 99% for my own use and really only up here in case somebody else has some use for it.

## Can I steal it?

I mean ... credit me if you would, but if not, maintenance's on you, and I will happily call you out if I see an addon with this code pop up in the store next week. Have fun! :P
