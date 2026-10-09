import dspy
from dspy.teleprompt import BootstrapFewShot

from ai_platform.dspy_setup import get_lm
from ai_platform.programs import TicketIntent

dspy.configure(lm=get_lm())


def ex(message, label):
    return dspy.Example(message=message, label=label).with_inputs("message")


trainset = [
    ex("I was charged twice this month", "billing"),
    ex("Please send me a copy of my invoice", "billing"),
    ex("My refund has not arrived yet", "billing"),
    ex("The app crashes when I open settings", "technical"),
    ex("I get error 500 on the dashboard", "technical"),
    ex("Page keeps loading and never finishes", "technical"),
    ex("I forgot my password", "account"),
    ex("How do I change my email address?", "account"),
    ex("Please delete my account", "account"),
    ex("Do you have a student discount program?", "other"),
    ex("What are your office hours?", "other"),
    ex("Can I talk to a human?", "other"),
]

devset = [
    ex("Why was my card billed on the 3rd?", "billing"),
    ex("The export button does nothing when clicked", "technical"),
    ex("I cannot log in, it says wrong credentials", "account"),
    ex("Where is your company located?", "other"),
    ex("Cancel my plan and give my money back", "billing"),
    ex("Upload fails with a timeout error", "technical"),
    ex("Update my phone number on my profile", "account"),
    ex("Do you sell gift cards?", "other"),
]


def metric(example, pred, trace=None):
    return example.label == pred.label


def accuracy(program, data) -> float:
    correct = 0
    for e in data:
        try:
            correct += int(metric(e, program(message=e.message)))
        except Exception as err:  # rate limit etc.
            print("skip:", type(err).__name__)
    return correct / len(data)


student = dspy.Predict(TicketIntent)
print(f"Before optimize: {accuracy(student, devset):.0%}")

optimizer = BootstrapFewShot(metric=metric, max_bootstrapped_demos=3, max_labeled_demos=3)
compiled = optimizer.compile(student, trainset=trainset)

print(f"After optimize : {accuracy(compiled, devset):.0%}")

compiled.save("optimized_intent.json")
print("Saved -> optimized_intent.json")

dspy.inspect_history(n=1)  # compiled prompt ma demos dekhase