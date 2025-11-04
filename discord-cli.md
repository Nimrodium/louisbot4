# CLI
Louisbot currently has a bad temporary interface, and should be rewritten

a new interface should be either using the actual discord command interface, or a better standard interface

the main commands needed for louisbot are maintenance commands and plot generation commands.

two types of plots exist, pie and line plots, with two data pools, messages and reactions.

thus a syntax could be 

`plot [type] [data] [range]`

`plot pie messages last 7 days`
`plot [type:pie] [data:messages/all] [range:last-7-days]`

`plot line messages last 7 days`
`plot line messages users [user1 user2] last week`

`plot line reactions users [ user user ] emojis [ emoji emoji ] last 7 days`
both a naive interface and a discord integrated command api interface could be supported at the same time.

