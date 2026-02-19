# Vibe Coding — Prompts Are All You Need?

*Using Software Construction Techniques like Test Driven Development and SOLID Principles for Effective Code Generation*

> And I was thinking to myself, this could be Heaven or this could be Hell,
> You can [git] check-in anytime you like, but you can never leave!
> And in the master's chambers,
> They gathered for the feast,
> They stab it with their steely knives
> But they just can't kill the Spaghetty beast
> So I asked the Captain for some TDD, and s/he said,
> "We do not have that Spirit here since ChatGPT"
>
> *(Author: ChatGPT 5 Generated)*

*Vibe Coding Heaven can become Hell if you are not careful*

---

Most coding will sooner or later be AI-assisted coding. AI coding agents are integrated so neatly into IDEs and work effectively that it is just a matter of time before they become an essential part of your development workflow.

Many sneer at vibe coders — those who do not know anything about programming or computer systems, but still, with a few prompts, can generate applications. Or those who know some programming and use AI with prompts for development.

As long as this is for some quick demo or proof of concept, there is no harm in this. But using AI exclusively without any in-depth knowledge to send code to production can be perilous. Not that AI writes bad code, because it is a powerful tool, and it needs a lot of knowledge to use this tool effectively.

It is not essential or possible to know everything, but it is essential to know the gaps in our knowledge. This is what separates the wise from the rest. This is a short article for all vibe coders and even younger/less-experienced coders on using AI-assisted coding effectively.

---

## Ask yourself this: Are you aware of Software Construction Techniques, or why they are needed?

Software is not like a statue that once shaped or cast remains as is. Software in the real world is extremely dynamic. You release a version, you realise there are some bugs, or if not, some new essential features to be added, or security holes. The list goes on endlessly, and you need to modify and ship the software.

Unless you have taken care of designing the software system to be able to modify or extend without side effects, your beautiful statue that was working and flawless when you shipped initially, you will see it distort and deform like the *Picture of Dorian Grey* within a few releases.

And experienced developers are going to scream at you or rant online about the bane of vibe-coders. The problem was never the Vibe coder. The problem was the programming culture in the company, which allowed code to go in without multiple reviews. Code review is so essential, like test-driven development, yet most software companies are managed and headed by non-technical managers who have no idea about the importance of these. A good system should safeguard against vibe coding pitfalls. It is also clear that many technical people have no leadership or team-building qualities and hence cannot be successful as managers in the first place. This is a dilemma which, if broken, can make the business extremely efficient and differentiated.

---

## So, what are Software Construction Techniques?

There is no rocket science to this. All these methods are essentially tackling system complexity by introducing abstractions in data types or function calls, or a combination thereof.

Let's start with the ubiquitous object-oriented programming paradigm.

Object-oriented programming tackles the deeper principles of software construction, like **encapsulation** (protection of internals) or **polymorphism** (extending behaviours without duplicating existing code).

The key to understanding object-oriented programming is the concept of **Data abstraction**, proposed by Barbara Liskov [21]. She received the 2008 Turing Award for her work in the development of object-oriented programming.

Basically, the concept of Classes — that they abstract a particular type, with methods associated with the type. This concept is then extended by subtyping called inheritance and more complex constructs like dynamic binding, which is selecting at run time the method associated with a type that is subclassed.

> `Dog` is a class that has some attributes like `breed`, `age`, etc and has some methods associated with it like `Dog.bark() -> "Woof"`. This is how these concepts are taught in classrooms. In the real world, programming these gets replaced by say `Class Printer`, attribute `type` (laser, deskjet), methods `loadPaper`, `Print`, etc.

Though not the first language, the one most popularising this concept was C with Classes, which was later named C++ and later Java.

This is not an article about object-oriented programming. Although very popular at one time, it is now fast fading. Good ideas turn to bad implementations in the hands of the masses. You can see very deep inheritance hierarchies and dynamic functions that are impossible to keep in mind in most older production codes — programmers going overboard with the concept, using it to create extremely complex structures for mental fun to the detriment of the next maintainer. Newer languages like Go are not object-oriented. But that does not mean that the core ideas are discarded.

To understand this in the context of Software construction, the book *Object-Oriented Software Construction* by Bertrand Meyer, which is freely available on his website, is a good read.

For example:

> *"Inheritance is a key technique for both reusability and extendibility"* — p. 516

So instead of duplicating code everywhere, use this concept. And then the core principle, the **Open-Closed Principle** — *Software should be closed for modification but open for extension* — and the related *Clean Code* (Robert C. Martin), *Single Responsibility Principle*.

---

## Vibe Coding and Extensibility: the Open-Closed Principle

And that is what it finally boils down to. If you have a nice painting of Dorian Grey, making a lot of modifications to the existing one is only going to ruin it. Touching old production code that is running fine has the same risk — the risk of side effects. Rather, you don't modify existing `SwitchingClass`; you subclass it like `SwitchingClassGermany` from `SwitchingClass` and use the new one for the new implementations in Germany. Over a decade, you will fix its bugs and make it rock solid. Existing global clients still use the old and stable `SwitchingClass` and have no side effects. This is the gist.

Say you don't have inheritance in your favourite language — Go — use it with interface and composition. Just ask ChatGPT for an example.

The key is to know what to ask when you vibe code and keep the principle of OCP in mind during design. That is a better way to vibe code.

The idea is not to overdo design, but to do just enough so that too many modifications to working code are avoided in the inevitable feature additions that come with all production software that someone is using.

**Example Prompt:**
```
Does this code follow SOLID principles — especially the Single Responsibility and Open-Closed principles?
Suggest how it can be restructured to improve extensibility and maintainability, without introducing
unnecessary complexity or overdesign.
```

---

## Vibe Coding and Maintainability

More time is spent maintaining production software than actually writing it, as code can run for years. It is essential to have good logs, summary counters, etc., as part of the code.

**Example Prompt:**
```
Improve the maintainability of this code. Add structured logging at key points (inputs, outputs, errors),
include summary counters or debug metrics if applicable, and ensure the code is readable and easy to
modify later. Avoid hardcoded values and add comments where necessary.
```

---

## Vibe Coding and Security

What's more? Many will yell Security — they will throw the thick OWASP reference on your face and yell about SQL injection or other such. Are they justified? Sure, they are. Security threats are real, and code has to take care of this. In defence, just make sure that you keep these aspects in mind while generating code. LLM engines like Codex medium and High and similar are really smart; you just have to tell them to keep these aspects or review your code with an explicit prompt. This does not mean that AI-generated code is foolproof; you will need some understanding or secondary reviews to confirm, especially for critical paths.

**Example Prompt:**
```
Please review this code for SQL injection, XSS, and other OWASP Top 10 issues. Suggest fixes.
```

> **Note:** Unless you are good at it, don't vibe code risky languages like C++ for production use.

---

## Test Test Test: Vibe Coding and TDD

My favourite paradigm of them all is **Test Driven Development (TDD)**. And this is a good way to catch AI-generated bugs as well. This was also very popular some time back and is losing its sheen. But the concepts it stands for are very much valid — as long as you don't go into the extreme camps where every acronym gets treated as a religion with blind faith or blind hate. The core idea is testing at the origin of code generation, thereby making code well tested and structured for easy testability at any level without extensive mocks and stubs. Whether you believe in TDD or not is irrelevant as long as the principle is met and based on your level of confidence. Defensive coding is usually as good as defensive driving, especially for the professional programmer.

There are two aspects to this:

1. **AI-generated code is usually good.** The subtle bugs in the code, which even the best models sometimes make, are extremely hard to find through review. You need good and diverse unit tests to figure these out.

2. **AI could generate code that you are not familiar with.** Instead of taking it as bug-free, use AI itself — with some thinking from your part — to write unit tests and test out the logic fully.

### One more time

AI-generated code will have very subtle bugs that are very hard to catch in the usual integration or end-to-end testing by your automated test suites and/or manual tests. The only way to catch these is during development with unit tests. This also makes your code testable.

It is very, very tempting to break this rule and rush to production; it is as risky as riding into a blind curve.

**Example Prompt:**
```
Write 5 well-structured unit tests for the following function. Cover a mix of typical use cases,
edge cases, and invalid inputs. Include tests for type overflows and the like. Document the intent
of each test case and the expected scenarios it covers.
```

> Without some understanding of the domain, you will not be able to effectively prompt. Use the AI itself to understand the code and then help in test generation.

---

## Does this really mean that Prompts are all you need now?

Not really. *"There is no royal road to Geometry"*, Euclid once said to a King who wanted the short version of Geometry.

There is only so much you can leverage. With more knowledge, the leverage is 100x multiplied. You need to spend time and effort, understand the core concepts and the application to understand Geometry. Same with anything. AI will help you learn faster.

You need to go to college so that you can get some time to learn software engineering. You need to work for some time so that you really understand the practical aspects of software construction and delivery. There is so much more to it than just writing.

I started my career in C++ chasing memory leaks and thread deadlocks, and stack corruptions. There was no glory at that time, just fear and stress and a prayer that this all would get over someday. In one test server, my code always crashed at one point during load runs. I could make no head or tail of it. Our company's veteran C++ instructor at that time told me that in his time, he used a hairdryer on the RAM board, so that faulty RAM chips would immediately fail. Though I did not try that extreme, it was a learning experience. And these things — among others, the ambiguity of human communications and importance of typed versioned interface and the like — only real experience will teach.

That's why, for sure, experienced programmers will still be needed and new programmers too, though much fewer than before. As there are things that only the real world will teach, and unless the new generation of programmers is taught to become experienced in time, the industry will be at the mercy of the LLM Gods.

---

*Published on [Towards AI](https://pub.towardsai.net/vibe-coding-prompts-are-all-you-need-1902215294bb) · October 31, 2025*
