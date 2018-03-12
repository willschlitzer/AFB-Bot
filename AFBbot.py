"""Bot to check Reddit comments and threads for USAF base ratings."""

import praw
import prawcore
import constants as c
import time
import bases
import weather


def reddit_login():
    """Creates instance of Reddit login."""
    if c.debuglogin:
        print("Logging in...")
    login = praw.Reddit(username=c.reddit_user,
                        password=c.reddit_pass,
                        client_id=c.reddit_api,
                        client_secret=c.reddit_secret,
                        user_agent="Air Force Base Bot /r/AFBbot")
    return login


comments_checked = []  # This is a fail safe for if the log fails to refrain from rechecking posts.
comment_checking = [None, None, None, None, None, None, None]



def checkbases(comment):
  """Checks all base instances and a comment for a rating."""
    linebreaktext = list(comment.body.lower())
    checktext = filtertext(linebreaktext).split()
    stringtext = ''.join(checktext)
    if bases.db.query_commentid(comment.id):  # Check log to see if comment is handled, will only happen on restarts.
        if c.debugsearch:
            print("I have already handled this comment. " + str(comment.id))
        pass
    elif "rate" in checktext and checkvalidrating(stringtext):
        for base in bases.all_bases:
            for name in base.names:
                if name in checktext:
                    if c.debugsearch:
                        print("User appears to be rating base.")
                    rating = getratingnumber(ratingfilter(list(comment.body.lower())))
                    if not c.debugnoreply:
                        rated_reply(comment, base, rating, "comment")
                    return True  # Prevents multiple base triggers creating multiple comments.
    else:
        for trigger in c.triggers:
            if trigger.lower() in checktext:
                if "stats" in checktext:
                    print("Replying with stats.")  # To do
                    return True
                else:
                    for base in bases.all_bases:
                        for name in base.names:
                            if name in checktext:
                                bases.db.log('reply', base.names[0], name, None, comment.id,
                                             comment.submission.id, None)
                                reply(comment, base)
                                return True  # Prevents multiple triggers creating multiple comments.


def checkbasesthread(thread):
    """Checks all base instances and a thread for a rating."""
    linebreaktext = list(thread.selftext.lower())
    checktext = filtertext(linebreaktext).split()
    stringtext = ''.join(checktext)
    global comments_checking
    if bases.db.query_commentid(thread.id):  # Check log to see if comment is handled, will only happen on restarts.
        if c.debugsearch:
            print("I have already handled this comment. " + str(thread.id))
        pass

    elif "rate" in checktext and checkvalidrating(stringtext):
        for base in bases.all_bases:
            for name in base.names:
                if name in checktext:
                    comments_checking[0] = name
                    if c.debugsearch:
                        print("User appears to be rating base.")
                    rating = getratingnumber(ratingfilter(list(thread.selftext.lower())))
                    comments_checking[2] = rating
                    rated_reply(thread, base, rating, "thread")
                    return True  # Prevents multiple base triggers creating multiple comments.
    else:
        for trigger in c.triggers:
            if trigger.lower() in checktext:
                if "stats" in checktext:  # To do
                    print("Replying with stats.")
                    return True
                else:
                    for base in bases.all_bases:
                        for name in base.names:
                            if name in checktext:
                                bases.db.log('reply', base.names[0], name, None, thread.id, thread.id, None)
                                reply(thread, base)
                                return True  # Prevents multiple triggers creating multiple comments.


def ratingfilter(text):
    """Filters characters from the rating text string."""
    noquotetext = filterqtext(text)
    for char in noquotetext:
        if char == "\n":
            noquotetext[char] = ""
    if c.debugsearch:
        print("start of filtered text: " + str(noquotetext))
    filterchars = '!@#$%^&*()+<>=,?:;'
    filteredtext = ''.join(noquotetext)
    filteredtext = filteredtext.replace("/", " ")
    if c.debugsearch:
        print(str(filteredtext))
    for char in filterchars:
        filteredtext = filteredtext.replace(char, "")
    checktext = filteredtext.split()
    if c.debugsearch:
        print(str(checktext))
    return checktext


def filtertext(text):
    """Filters characters from the comment or thread text string."""
    noquotetext = filterqtext(text)
    if c.debugsearch:
        print(noquotetext)
    for i in range(len(noquotetext)):
        if noquotetext[i] == "'":
            noquotetext[i] = ""
    filterchars = '!@#$%^&*()/-;+<>=,.?:'
    filteredtext = ''.join(noquotetext)
    for char in filterchars:
        filteredtext = filteredtext.replace(char, "")
    if c.debugsearch:
        print("Symbols have been removed: " + str(filteredtext))
    checktext = ''.join(filteredtext)
    if c.debugsearch:
        print("Final check to text: " + checktext)
    return checktext


def filterqtext(text):
    """Prevents replying to quoted text and keeps punctuated text checked"""
    checkquote = text
    if c.debugsearch:
        print("I am checking" + (str(text)) + "for a quote mark, I see " + str(checkquote[0][0]))
    if checkquote[0][0] == '>':
        if c.debugsearch:
            print("Quote found")
        if "\n" in checkquote:
            for z in range(len(checkquote)):
                for char2 in checkquote[z]:
                    if char2 == '\n':
                        if c.debugsearch:
                            print("Line break found")
                            print("Quote: " + str(checkquote))
                        del checkquote[0:(z + 2)]
                        if ">" in checkquote:
                            if c.debugsearch:
                                print("Multi quote comment, will not reply.")
                            return ""
                        else:
                            return checkquote
            else:
                if c.debugsearch:
                    print("No line break found, not replying.")
                return ""
    elif ">" in checkquote:
        if c.debugsearch:
            print("Quote within the text, will noy reply.")
        return ""
    return checkquote


def checkvalidrating(comment):
    """Validates rating if debugsearch is enabled."""
    splitlist = comment.split("rate")
    del splitlist[0]
    joinedlist = ''.join(splitlist)
    if c.debugsearch:
        print(str(joinedlist))
    numbers = [int(x) for x in comment if x.isdigit()]
    if c.debugsearch:
        print(str(numbers))
    if c.debugsearch:
        print("Checking if the rating is valid, I found these numbers: " + str(numbers) + "Length "
              + str(len(numbers)))
    if len(numbers) < 1:
        if c.debugsearch:
            print("No numbers, returning with a reply instead of a rating")
        return False
    else:
        return True


def getratingnumber(text):
    """Determines the rating of a base.

    Detects the usage of 'rate' in a string,
    determines the base and rating, and returns a rating.
    """
    delete = []  # deletes everything up to and including the indexes "rate"
    for i in range(len(text)):
        word = text[i]
        if word == 'rate':
            for z in range(0, i):
                delete.append(z)
            continue
    for i in sorted(delete, reverse=True):
        del text[i]

    delete = []  # deletes every index that begins with an alpha character, only need numbers/periods at this point.
    for i in range(len(text)):
        word = list(text[i])
        realword = word[0]
        if realword.isalpha():
            delete.append(i)
            continue
    for i in sorted(delete, reverse=True):
        del text[i]

    finalnumber = []

    for char in text:
        number = []
        appenededperiod = False  # Handles decimals and extra periods, places the first one it finds in the number.
        charlist = list(char)
        for i in range(len(charlist)):
            if charlist[i] == ".":
                if not appenededperiod:
                    number.append(".")
                    appenededperiod = True
            else:
                number.append(str(charlist[i]))
        if c.debugsearch:
            print(str(number))
        truenumber = ''.join(str(i) for i in number)
        finalnumber.append(truenumber)
    if c.debugsearch:
        print(str(finalnumber))

    numbers = [float(x) for x in finalnumber if not x.isalpha()]
    if c.debugsearch:
        print(str(numbers))

    if numbers[0] > 10:
        return 10.00
    elif 1 <= numbers[0] <= 10:
        rounded = "%.2f" % numbers[0]
        return rounded
    elif numbers[0] <= 1:
        return 1.00
    else:
        print("Something weird happened with the getrating number, " + str(numbers[0]))
        return 10.00


def reply(comment, base):
    """Replies to a comment with the base rating."""
    print("Adding reply to " + str(comment.id))
    if not c.debugnoreply:
        comment.reply(f"""{base.displayname}{base.getmajcom()} is located in {base.location}\n\n
{weather.getweather(base.location)}
Base rating: {str(base.getrating())}/10 out of {str(bases.db.count_ratings(base.names[0]))} ratings.\n\n"""
                      + c.bot_signature)


def rated_reply(comment, base, rating, self):
    """Acknowledges a base rating and replies with the updated rating"""
    if self == "comment":
        print("Adding rating to " + str(comment.id))  # Checks if they have already added a rating to this base
        if base.addrating(str(comment.author), rating, comment.id, comment.submission.id):
            if not c.debugnoreply:
                comment.reply(f'''Your rating has been added to {base.displayname}.\n\n
Base rating: {str(base.getrating())}/10 out of {str(bases.db.count_ratings(base.names[0]))} ratings.\n\n'''
                              + c.bot_signature)
        else:
            base.changerating(str(comment.author), rating, comment.id, comment.submission.id)
            if not c.debugnoreply:
                comment.reply(f'''Your rating of {base.displayname} has been changed to {str(rating)}.  
Base rating: {str(base.getrating())}/10 out of {str(bases.db.count_ratings(base.names[0]))} ratings.\n\n'''
                              + c.bot_signature)
    else:
        print("Adding rating to " + str(comment.id))
        if base.addrating(str(comment.author), rating, comment.id,
                          comment.id):
            if not c.debugnoreply:  # Checks if they have already added a rating to this base
                comment.reply(f'''Your rating has been added to {base.displayname}.\n\n
Base rating: {str(base.getrating())}/10 out of {str(bases.db.count_ratings(base.names[0]))} ratings.\n\n'''
                              + c.bot_signature)
        else:
            base.changerating(str(comment.author), rating, comment.id, comment.id)
            if not c.debugnoreply:
                comment.reply(f'''Your rating of {base.displayname} has been changed to {str(rating)}.  
Base rating: {str(base.getrating())}/10 out of {str(bases.db.count_ratings(base.names[0]))} ratings.\n\n'''
                              + c.bot_signature)


def bot_main(login):
    """Uses Reddit instance to check comments and threads."""
    global comments_checking
    try:
        comments_checking = [None, None, None, None, None, None, None]
        session = login
        if c.debugsearch:
            print("Checking comments...")
        for sub in c.reddit_subs:
            if c.debugsearch:
                print("Checking in sub " + str(sub))
            for comment in session.subreddit(sub).comments(limit=20):  # Need to check for locked thread, throws except
                if comment.id not in comments_checked and comment.author != c.reddit_user\
                        and len(comment.body.lower()) > 0:
                    comments_checking[1] = comment.author
                    comments_checking[3] = comment.id
                    comments_checking[4] = comment.submission.id
                    if c.debugsearch:
                        print("Comment " + str(comment.id) + " is not in " + str(comments_checked))
                    comments_checked.append(comment.id)
                    checkbases(comment)
                else:
                    continue
            if c.debugsearch:
                print("Checking threads...")
            for thread in session.subreddit(sub).new(limit=5):
                if thread.id not in comments_checked and len(thread.selftext.lower()) > 0:
                    comments_checking[1] = thread.author
                    comments_checking[3] = thread.id
                    comments_checking[4] = thread.id
                    comments_checked.append(thread.id)
                    checkbasesthread(thread)

    except prawcore.exceptions.ResponseException as e:
        print("Response error, server probably busy. Sleeping and retrying. " + str(e))
        time.sleep(60)

    except prawcore.exceptions.OAuthException as e:
        bases.db.log('Login Error', None, None, None, None, None, str(e))
        print("Invalid credentials while logging in!")
        time.sleep(60)

    except ConnectionError as e:
        print("Connection error, sleeping and retrying. " + str(e))
        time.sleep(60)

    except Exception as e:
        print(f"Logging {comments_checking[0]} {comments_checking[1]} {comments_checking[2]} {comments_checking[3]} {comments_checking[4]} {e}")
        bases.db.log('Error', str(comments_checking[0]), str(comments_checking[1]), comments_checking[2],
                     str(comments_checking[3]), str(comments_checking[4]), str(e))
    else:
        if c.debugsearch:
            print("Completed loop successfully.")

    finally:
        if c.debugsearch:
            print("Sleeping...")
        time.sleep(30)


if __name__ == "__main__":
    print("Running...")
    if c.createdb:
        bases.maketables()

    while True:  # Main loop
        bot_main(reddit_login())
