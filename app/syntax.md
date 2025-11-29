# Louisbot Help
## commands
* ping
> pings the bot
* process
> forces the bot to process the current batch of messages
* flush
> forces the bot to flush data to disk
* plot
> plot a graph

### plot syntax
> `<...> is required, (...)=x is optional with default value of x, | is or. : annotates a type, so <a|b|c>:int means must provide an int of a, b, or c `
`plot <pie|line> <messages|reactions> (hours|days)=days (users: <a|[a]|[a ...]>:list[str])=calling_user (emojis: <a|[a]|[a ...]>:list[str]) (<past a:int <days|weeks|months|years>|since a:nt|from a:nt to b:nt>) where nt = natural_language`
the emoji list is required when using the reactions mode
some example commands:
* `plot line messages`
> plots a line chart of the last 7 days of your messages, equivilent to `plot line messages users: YOUR_USERNAME past 7 days`
