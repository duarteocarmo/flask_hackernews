def calculate_score(votes, item_hour_age, gravity=1.8):
      return (votes - 1) / pow((item_hour_age+2), gravity)


upvote_possib = [10]
for hour in range(10):
    for upvotes in upvote_possib:
        print(f"Hour:{hour}\tVotes:{upvotes}\tScore:{calculate_score(upvotes, hour)}")