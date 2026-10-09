"""
AI Service Module - InterviewIQ
Handles communication with external LLM providers (OpenAI, Gemini, OpenAI-compatible)
and provides a fully deterministic local DemoAIService when credentials are not configured.
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


# Deterministic Question Banks by Domain and Difficulty for Demo Mode
DOMAIN_QUESTION_BANKS = {
    'Data Structures and Algorithms': {
        'Easy': [
            {
                'text': 'Let us start with fundamental memory structures. In software engineering, we frequently evaluate the trade-offs between sequential contiguous storage like an Array and pointer-linked nodes like a Linked List. Could you walk me through how they differ in CPU cache locality, memory allocation overhead, and random access complexities? Give me a realistic scenario where an array would be vastly superior to a linked list.',
                'target_concept': 'Contiguous memory vs pointer-based nodes; O(1) random access vs O(n) traversal; cache line hits vs pointer overhead',
                'category': 'Data Structures',
                'difficulty': 'Easy'
            },
            {
                'text': 'Now let us talk about the Stack data structure and recursion. How does a Stack enforce the Last-In First-Out principle under the hood, and how does the operating system or language runtime utilize a call stack during recursive function calls? What happens when recursion exceeds allocated limits?',
                'target_concept': 'LIFO principle; call stack frames, stack overflow, push and pop O(1) complexity',
                'category': 'Data Structures',
                'difficulty': 'Easy'
            },
            {
                'text': 'Let us examine search efficiency. What is the time complexity of Binary Search compared to Linear Search, what strict mathematical precondition must the input collection satisfy, and how would you avoid integer overflow when calculating the middle index in languages like Java or C++?',
                'target_concept': 'O(log n) vs O(n); sorted array precondition; mid calculation (low + (high - low) / 2)',
                'category': 'Algorithms',
                'difficulty': 'Easy'
            }
        ],
        'Medium': [
            {
                'text': 'Let us explore Hash Tables and collision resolution. When two keys produce the identical hash bucket index, systems typically choose between Separate Chaining and Open Addressing like linear or quadratic probing. Could you explain how both methods resolve collisions, what happens to lookup performance when the load factor increases, and what worst-case time complexity can occur?',
                'target_concept': 'Chaining with linked lists/red-black trees vs open addressing; load factor rehashing; O(1) average vs O(n) worst case',
                'category': 'Data Structures',
                'difficulty': 'Medium'
            },
            {
                'text': 'Suppose you are building a graph or linked data parser and need to detect cycles without altering the node structures. How does Floyd\'s Tortoise and Hare cycle-finding algorithm work in O(1) auxiliary space, and why are we mathematically guaranteed that the fast pointer will eventually overlap with the slow pointer if a cycle exists?',
                'target_concept': "Floyd's Cycle-Finding Algorithm; slow and fast two pointers; O(1) auxiliary space and O(n) time complexity",
                'category': 'Algorithms',
                'difficulty': 'Medium'
            },
            {
                'text': 'Let us discuss graph and tree traversals. How does Breadth-First Search differ from Depth-First Search in terms of memory requirements and the underlying data structures used? In what specific real-world problems, such as finding the shortest path in an unweighted social network graph, is BFS strictly required?',
                'target_concept': 'Queue vs Stack/Recursion; level-order shortest path in unweighted graphs; O(V + E) time complexity',
                'category': 'Algorithms',
                'difficulty': 'Medium'
            },
            {
                'text': 'Consider sorting algorithms in production environments. QuickSort and MergeSort both offer O(n log n) average performance. Why does standard library implementations like Python\'s Timsort or C++ std::sort prefer hybrid approaches? What are the space complexity trade-offs of MergeSort compared to in-place QuickSort?',
                'target_concept': 'O(n) auxiliary space for MergeSort vs O(log n) call stack in QuickSort; stable sorting vs pivot degradation to O(n^2)',
                'category': 'Algorithms',
                'difficulty': 'Medium'
            }
        ],
        'Hard': [
            {
                'text': 'Let us tackle system-level data structures. Suppose you need to design a high-throughput in-memory Least Recently Used, or LRU, Cache. Walk me through your design combining a doubly linked list with a hash map. How do you ensure that both get and put operations execute in guaranteed constant O(1) time complexity while maintaining thread safety?',
                'target_concept': 'Doubly linked list paired with hash map; O(1) get and put; eviction logic; synchronization locks',
                'category': 'System & Data Structures',
                'difficulty': 'Hard'
            },
            {
                'text': 'Let us examine dynamic programming versus greedy paradigms. For the classic Knapsack problem, explain why a greedy approach achieves optimal results for Fractional Knapsack but completely fails for the 0/1 Knapsack problem. What is the DP state transition relation and its pseudo-polynomial time complexity?',
                'target_concept': 'Greedy density ratio vs overlapping subproblems; DP state table dp[i][w] = max(dp[i-1][w], val + dp[i-1][w-wt]); pseudo-polynomial O(n*W)',
                'category': 'Dynamic Programming',
                'difficulty': 'Hard'
            }
        ]
    },
    'Python': {
        'Easy': [
            {
                'text': 'Let us explore Python data structures and memory allocation. Beginners often distinguish lists from tuples simply by saying lists are mutable while tuples are immutable. Beyond mutability, how do lists and tuples differ in internal memory over-allocation, performance, and hashability? Why can a tuple containing strings serve as a dictionary key while a list cannot?',
                'target_concept': 'Mutability vs immutability; hashability (__hash__); over-allocation resizing in list vs fixed tuple allocation',
                'category': 'Core Python',
                'difficulty': 'Easy'
            },
            {
                'text': 'How does Python handle automatic memory management under the hood? Walk me through reference counting as the primary mechanism, how cyclic reference garbage collection detects circular references, and what role the gc module plays in performance-critical services.',
                'target_concept': 'Reference counting with cyclic generational garbage collector; PyObject refcount; gc generations 0, 1, 2',
                'category': 'Runtime Internals',
                'difficulty': 'Easy'
            }
        ],
        'Medium': [
            {
                'text': 'Let us dive into concurrency in CPython. What exactly is the Global Interpreter Lock, or GIL, and why was it introduced? How does the GIL affect multithreaded CPU-bound tasks versus I/O-bound tasks, and how should a Python engineer architect a service that requires true multi-core parallel processing?',
                'target_concept': 'Mutex protecting CPython memory management; CPU-bound thread contention vs I/O-bound async/threading; multiprocessing module',
                'category': 'Concurrency',
                'difficulty': 'Medium'
            },
            {
                'text': 'Can you explain what Python Generators and the yield keyword do under the hood? Walk me through what happens to the function frame and local variable state when yield is reached, and explain why generators are critical when processing gigabytes of log files or streaming API data.',
                'target_concept': 'Lazy evaluation; generator frame state suspension; iterator protocol (__iter__, __next__); memory footprint reduction',
                'category': 'Advanced Python',
                'difficulty': 'Medium'
            },
            {
                'text': 'How do Python decorators work from a functional programming perspective? Could you walk me through how you would implement a custom decorator that accepts configuration arguments, measures and logs execution time, and properly preserves original function metadata using functools.wraps?',
                'target_concept': 'Higher-order functions; three-tier nested closure for parameterized decorators; functools.wraps preserving __name__ and __doc__',
                'category': 'Advanced Python',
                'difficulty': 'Medium'
            }
        ],
        'Hard': [
            {
                'text': 'Let us discuss Python metaprogramming and internals. How do metaclasses differ from standard class inheritance, and how does the __new__ method differ from __init__ in class creation? Can you describe a scenario where writing a custom metaclass or utilizing __init_subclass__ is justified in library or framework development?',
                'target_concept': 'Metaclass as class of a class (type); __new__ object allocator vs __init__ initializer; class registration and validation via __init_subclass__',
                'category': 'Metaprogramming',
                'difficulty': 'Hard'
            }
        ]
    },
    'DBMS and SQL': {
        'Easy': [
            {
                'text': 'Let us examine relational querying fundamentals. What is the fundamental operational difference between the WHERE clause and the HAVING clause in SQL? In what order does the database engine process them relative to GROUP BY aggregations, and can you provide a scenario where combining both is necessary?',
                'target_concept': 'WHERE filters raw rows before aggregation; HAVING filters aggregated groups; SQL execution order (FROM, WHERE, GROUP BY, HAVING, SELECT)',
                'category': 'SQL Queries',
                'difficulty': 'Easy'
            },
            {
                'text': 'What is a Primary Key in relational databases, how does it differ from a Unique Key constraint, and can a table have multiple unique keys? What are the implications of NULL values in unique constraints across SQL standards?',
                'target_concept': 'Single primary key cannot be NULL; multiple unique keys allow NULL depending on SQL dialect; clustered vs non-clustered indexes',
                'category': 'Database Design',
                'difficulty': 'Easy'
            }
        ],
        'Medium': [
            {
                'text': 'Let us discuss database transactions and reliability. Walk me through the ACID properties of relational database engines. In particular, explain why transaction isolation levels matter, and what phenomena like dirty reads, non-repeatable reads, and phantom reads mean in a multi-user banking system.',
                'target_concept': 'Atomicity, Consistency, Isolation, Durability; isolation levels (Read Uncommitted, Read Committed, Repeatable Read, Serializable); concurrency anomalies',
                'category': 'Transactions & Concurrency',
                'difficulty': 'Medium'
            },
            {
                'text': 'What is Database Normalization, and what specific anomalies does it prevent? Walk me through First Normal Form (1NF), Second Normal Form (2NF), and Third Normal Form (3NF) using a simple college student and enrollment database example.',
                'target_concept': 'Insertion, update, and deletion anomalies; 1NF atomic columns; 2NF removing partial key dependency; 3NF removing transitive dependency',
                'category': 'Schema Architecture',
                'difficulty': 'Medium'
            },
            {
                'text': 'How do Database Indexes accelerate query performance, and what data structures are most commonly chosen by database storage engines like InnoDB or PostgreSQL? What are the write performance penalties and storage costs associated with over-indexing tables?',
                'target_concept': 'B-Tree / B+ Tree indexing; fast lookups and range scans; write amplification on INSERT/UPDATE/DELETE; index maintenance overhead',
                'category': 'Indexing & Optimization',
                'difficulty': 'Medium'
            }
        ],
        'Hard': [
            {
                'text': 'Compare B-Trees and B+ Trees in depth. Why do production relational storage engines store table row pointers and records strictly in leaf nodes linked as a doubly linked list, rather than storing data records directly inside interior index nodes as standard B-Trees do?',
                'target_concept': 'B+ Tree leaf data pointers; high fanout and shallow tree height; sequential range scan efficiency via leaf pointer chain; cache line optimization',
                'category': 'Storage Engines',
                'difficulty': 'Hard'
            }
        ]
    },
    'Java': {
        'Easy': [
            {
                'text': 'Let us discuss Java memory and object orientation. What is the fundamental difference between the Java Stack and the Java Heap memory regions? Where do local primitive variables reside versus object instances, and what happens when an object reference is passed into a method?',
                'target_concept': 'Stack stores method frames and local primitives; Heap stores objects; Java is strictly pass-by-value of reference values',
                'category': 'Java Fundamentals',
                'difficulty': 'Easy'
            },
            {
                'text': 'What is the contract between equals() and hashCode() in Java? Why must you always override hashCode() whenever you override equals(), and what breaking bugs occur in HashSets or HashMaps if this contract is violated?',
                'target_concept': 'If two objects are equal according to equals(), their hashCode() must be identical; bucket lookup failure in HashMap',
                'category': 'Core Java',
                'difficulty': 'Easy'
            }
        ],
        'Medium': [
            {
                'text': 'How does Garbage Collection in the Java Virtual Machine operate? Walk me through generational garbage collection dividing heap into Young Generation (Eden and Survivor spaces) and Old Generation, and explain what a Stop-The-World pause represents in production applications.',
                'target_concept': 'Generational hypothesis; Eden, S0, S1, Tenured space; Minor GC vs Major/Full GC; Stop-the-world pauses; G1GC vs ZGC',
                'category': 'JVM Architecture',
                'difficulty': 'Medium'
            },
            {
                'text': 'Explain Java Concurrency mechanisms. What is the difference between synchronized blocks, volatile keywords, and Atomic classes like AtomicInteger? What is the Java Memory Model, and why does volatile prevent instruction reordering without providing compound atomicity?',
                'target_concept': 'synchronized mutex vs volatile visibility/happens-before memory barrier; CAS (Compare-And-Swap) in AtomicInteger; compound increment vulnerability',
                'category': 'Java Concurrency',
                'difficulty': 'Medium'
            }
        ],
        'Hard': [
            {
                'text': 'How does Java 21 Virtual Threads (Project Loom) revolutionize concurrent server architecture compared to traditional platform threads? Explain how continuation suspension and carrier threads eliminate reactive callback complexity while handling millions of concurrent I/O connections.',
                'target_concept': 'Virtual threads vs OS platform threads; carrier thread pool; continuations park on I/O without blocking OS thread; thread-per-request simplicity',
                'category': 'Java Internals',
                'difficulty': 'Hard'
            }
        ]
    },
    'Operating Systems': {
        'Easy': [
            {
                'text': 'Let us start with foundational process management. What is the technical difference between a Process and a Thread? How do their memory spaces, file descriptors, and context-switching overheads compare in modern operating systems like Linux or Windows?',
                'target_concept': 'Independent virtual address space vs shared process memory; PCB vs TCB; context switch cache invalidation cost',
                'category': 'Process Management',
                'difficulty': 'Easy'
            }
        ],
        'Medium': [
            {
                'text': 'What is a Deadlock in concurrent systems, and what are the four necessary Coffman conditions that must all hold simultaneously for a deadlock to occur? Walk me through how an operating system or database can prevent or break deadlocks.',
                'target_concept': 'Mutual Exclusion, Hold and Wait, No Preemption, Circular Wait; lock ordering hierarchy, Banker algorithm, resource graph cycle detection',
                'category': 'Concurrency & Deadlocks',
                'difficulty': 'Medium'
            },
            {
                'text': 'Can you explain the architecture of Virtual Memory and Demand Paging? What happens step-by-step when a program triggers a Page Fault? Walk me from the Memory Management Unit, or MMU, translation failure to disk swap retrieval and TLB update.',
                'target_concept': 'MMU address translation, Page Tables, Page Fault interrupt, OS disk retrieval from swap space, frame allocation, TLB cache update',
                'category': 'Memory Management',
                'difficulty': 'Medium'
            }
        ],
        'Hard': [
            {
                'text': 'What is Thrashing in an operating system, and how does excessive page faulting degrade CPU utilization to near zero? Explain how the Working Set Model or Page Fault Frequency algorithm monitors process locality of reference to prevent thrashing in multi-tenant environments.',
                'target_concept': 'Thrashing due to over-allocated memory; disk I/O saturation; working set size calculation; page replacement throttling',
                'category': 'Memory Management',
                'difficulty': 'Hard'
            }
        ]
    },
    'Computer Networks': {
        'Easy': [
            {
                'text': 'Let us examine transport protocols. What are the key architectural differences between TCP and UDP? Walk me through reliability, packet ordering, and flow control. Give me a clear example of an application that strictly requires TCP and another that benefits from UDP.',
                'target_concept': 'Connection-oriented reliable delivery with checksums and sequence numbers vs connectionless datagram stream; HTTP/File transfer vs VoIP/Gaming',
                'category': 'Transport Layer',
                'difficulty': 'Easy'
            }
        ],
        'Medium': [
            {
                'text': 'Walk me through what happens under the hood when a user types https://example.com into their browser and presses Enter. Trace the request from local DNS resolution, TCP three-way handshake, TLS 1.3 cryptographic handshake, HTTP GET request, through to server response and browser DOM rendering.',
                'target_concept': 'DNS recursive resolution, TCP SYN/SYN-ACK/ACK, TLS key exchange and certificate verification, HTTP request/response, DOM tree rendering',
                'category': 'Network Protocols',
                'difficulty': 'Medium'
            },
            {
                'text': 'Explain how TCP Congestion Control functions. What are the roles of the congestion window, slow start threshold, and how do algorithms like Slow Start, Congestion Avoidance, and Fast Retransmit recover from packet drops in high-latency links?',
                'target_concept': 'cwnd, ssthresh, exponential increase in slow start, additive increase multiplicative decrease (AIMD), duplicate ACKs triggering fast retransmit',
                'category': 'Transport Layer',
                'difficulty': 'Medium'
            }
        ],
        'Hard': [
            {
                'text': 'How does HTTP/2 multiplexing work compared to HTTP/1.1 pipelining, and why did HTTP/3 transition from TCP to the QUIC protocol over UDP to solve head-of-line blocking at the transport layer?',
                'target_concept': 'Binary framing, streams over single TCP connection in HTTP/2; TCP head-of-line blocking on packet loss; QUIC independent UDP streams and 0-RTT handshakes',
                'category': 'Application Protocols',
                'difficulty': 'Hard'
            }
        ]
    },
    'JavaScript': {
        'Easy': [
            {
                'text': 'Let us examine variable scoping and hoisting in JavaScript. What are the differences between var, let, and const in terms of scope, redeclaration, and the Temporal Dead Zone? What happens under the hood when JavaScript hoists variable declarations during the compilation phase?',
                'target_concept': 'Function scope vs block scope; temporal dead zone (TDZ) for let/const; hoisting declarations vs initializations',
                'category': 'Core JavaScript',
                'difficulty': 'Easy'
            }
        ],
        'Medium': [
            {
                'text': 'Can you explain the JavaScript Event Loop, Call Stack, Microtask Queue, and Macrotask Queue? Given code containing a synchronous console.log, a Promise.resolve callback, and a setTimeout with zero delay, in what exact order will they execute and why do microtasks take priority?',
                'target_concept': 'Single-threaded event loop; call stack execution; Promise microtasks drain completely before next macrotask (setTimeout/setInterval)',
                'category': 'Asynchronous JS',
                'difficulty': 'Medium'
            },
            {
                'text': 'What are Closures in JavaScript? How does a closure preserve access to its lexical scope even after the outer function has completed execution? Provide a practical scenario, such as data privacy or function memoization, where closures are essential.',
                'target_concept': 'Lexical scope retention in heap; data encapsulation/private variables; currying and memoization factory patterns',
                'category': 'Functions & Scope',
                'difficulty': 'Medium'
            }
        ],
        'Hard': [
            {
                'text': 'Walk me through JavaScript prototypal inheritance under the hood. How does the prototype chain (__proto__ vs prototype) resolve property lookups, and how do ES6 classes map to prototypal inheritance behind their syntactic sugar?',
                'target_concept': 'Prototype chain traversing up to Object.prototype and null; Object.create(); constructor functions and prototype linkage',
                'category': 'Prototypes',
                'difficulty': 'Hard'
            }
        ]
    },
    'React': {
        'Easy': [
            {
                'text': 'Let us examine React rendering architecture. What is the Virtual DOM, and how does React reconciliation algorithm determine which real DOM nodes require mutation? Why is updating the real DOM directly in plain JavaScript slower than batched reconciliation?',
                'target_concept': 'In-memory lightweight tree; diffing algorithm O(n); batching real browser reflow and repaint operations',
                'category': 'Core React',
                'difficulty': 'Easy'
            }
        ],
        'Medium': [
            {
                'text': 'What are the distinct responsibilities of useEffect, useMemo, and useCallback hooks? When does premature or unnecessary use of useMemo actually harm performance instead of improving it, and how does referential equality affect child component re-renders?',
                'target_concept': 'Side effects vs memoized values vs stable function references; memory allocation and dependency array comparison cost in useMemo',
                'category': 'React Hooks',
                'difficulty': 'Medium'
            }
        ],
        'Hard': [
            {
                'text': 'Explain how React Server Components, or RSC, fundamentally alter client bundle sizes and data fetching pipelines compared to standard client-rendered Single Page Applications or traditional Next.js getServerSideProps.',
                'target_concept': 'Zero client bundle size for server components; streaming SSR with selective hydration; direct database/backend access without API routes',
                'category': 'Architecture',
                'difficulty': 'Hard'
            }
        ]
    },
    'HR Interview': {
        'Easy': [
            {
                'text': 'Welcome to the HR round. Could you introduce yourself, walk me through your engineering degree coursework, and tell me what motivated you to pursue a software engineering career over other technical paths?',
                'target_concept': 'Structured self-introduction, authentic passion for coding and engineering problem solving',
                'category': 'Self-Introduction',
                'difficulty': 'Easy'
            },
            {
                'text': 'Why are you specifically interested in joining our company for this placement role, and what about our technology stack or product mission aligns with your personal goals?',
                'target_concept': 'Company research, culture alignment, technology learning curve',
                'category': 'Company Motivation',
                'difficulty': 'Easy'
            }
        ],
        'Medium': [
            {
                'text': 'Tell me about a challenging situation where you had a disagreement with a project team member or classmate regarding technical architecture or work distribution. Using the STAR method, how did you handle the situation and achieve a positive outcome?',
                'target_concept': 'STAR format (Situation, Task, Action, Result); active listening, empathy, objective technical trade-offs',
                'category': 'Conflict Resolution',
                'difficulty': 'Medium'
            },
            {
                'text': 'Describe a project where you encountered a critical technical blocker, deadline pressure, or unexpected bug. How did you organize your priorities, communicate progress with your mentor or team, and maintain composure?',
                'target_concept': 'Resilience, problem decomposition, transparent communication under pressure',
                'category': 'Stress & Problem Solving',
                'difficulty': 'Medium'
            }
        ],
        'Hard': [
            {
                'text': 'Where do you envision yourself professionally in 3 to 5 years? How does this entry-level engineering role serve as the foundation for your long-term roadmap in software development, architecture, or technical leadership?',
                'target_concept': 'Career roadmap, technical mastery, ownership, ambition paired with realistic growth expectations',
                'category': 'Career Vision',
                'difficulty': 'Hard'
            }
        ]
    }
}

GENERIC_TECHNICAL_QUESTIONS = [
    {
        'text': 'Could you walk me step-by-step through your systematic debugging methodology when you encounter an intermittent runtime crash or memory leak in a production service? What profiling tools or logging practices do you rely on?',
        'target_concept': 'Reproducing issues, stack trace analysis, binary search debugging (git bisect), memory profiling, unit test isolation',
        'category': 'Software Engineering',
        'difficulty': 'Medium'
    },
    {
        'text': 'How do you approach writing clean, maintainable, self-documenting code, and what specific role do automated unit and integration tests play in your day-to-day software development workflow?',
        'target_concept': 'Clean architecture, SOLID principles, test-driven development, regression prevention, code reviews',
        'category': 'Software Engineering',
        'difficulty': 'Medium'
    },
    {
        'text': 'Explain the difference between synchronous and asynchronous architectures. In what scenarios is asynchronous non-blocking event-driven I/O preferred over multi-threaded blocking I/O, and what are the trade-offs in debugging complexity?',
        'target_concept': 'Blocking vs non-blocking I/O; concurrency vs parallelism; event loop efficiency; asynchronous tracing complexity',
        'category': 'System Architecture',
        'difficulty': 'Medium'
    }
]


class BaseAIService:
    """Base interface for interview AI interactions."""
    def generate_first_question(self, session) -> Dict[str, Any]:
        raise NotImplementedError

    def evaluate_answer(self, session, question, answer_text: str, conversation_history: List[Dict]) -> Dict[str, Any]:
        raise NotImplementedError

    def generate_next_question(self, session, conversation_history: List[Dict], previous_evaluations: List[Dict]) -> Dict[str, Any]:
        raise NotImplementedError

    def generate_final_report(self, session, full_transcript: List[Dict], evaluations: List[Dict]) -> Dict[str, Any]:
        raise NotImplementedError


class DemoAIService(BaseAIService):
    """
    Deterministic rule-based local service when no external AI API key is configured.
    Does NOT pretend to be real AI. Clearly discloses its deterministic demo nature.
    """

    def generate_first_question(self, session) -> Dict[str, Any]:
        return {
            'text': (
                f"Hello and welcome to your {session.interview_type} for {session.technical_domain}! "
                "I will be conducting your placement interview today. To get started, please introduce yourself, "
                "share your academic background, and tell me about the key projects or technologies you enjoy working on."
            ),
            'target_concept': 'Structured self-introduction, communication confidence, academic background, technical interests',
            'category': 'Candidate Introduction',
            'difficulty': 'Easy',
            'interviewer_note': '[DEMO MODE: Opening candidate introduction before technical round]'
        }

    def evaluate_answer(self, session, question, answer_text: str, conversation_history: List[Dict]) -> Dict[str, Any]:
        """Deterministic rule-based evaluation of candidate answer."""
        text_lower = answer_text.strip().lower()
        word_count = len(re.findall(r'\b\w+\b', text_lower))

        # Check for explicit "I don't know" or empty
        idk_phrases = ["i don't know", "i do not know", "no idea", "not sure", "don't know", "skip", "pass", "no clue"]
        is_idk = any(phrase in text_lower for phrase in idk_phrases) and word_count < 15

        # Handle Candidate Introduction specially
        if question.category == 'Candidate Introduction' or 'introduce yourself' in question.text.lower():
            if is_idk or word_count < 8:
                classification = 'Needs clarification'
                score = 55.0
                interviewer_response = "Could you tell me a little bit more about yourself, your degree, and what areas of software development you enjoy?"
                correct_concepts = ["Attempted introduction"]
                missing_concepts = ["Academic details", "Projects or technical focus"]
                incorrect_statements = []
                explanation = "[DEMO MODE: Rule-based local evaluation] Introduction was too brief. Share your background, key technologies, and aspirations."
                suggestions = "Structure your introduction: 1) Who you are & education, 2) Core technical skills & projects, 3) Enthusiasm for this role."
                better_answer = f"I am a final-year engineering student. My primary technical stack includes {session.technical_domain}. Recently, I built a project involving..."
                follow_up_needed = True
                suggested_follow_up = "What particular project or technology have you enjoyed working with the most during your studies?"
            else:
                classification = 'Correct' if word_count >= 25 else 'Mostly correct'
                score = 92.0 if word_count >= 25 else 80.0
                interviewer_response = (
                    f"Thank you for sharing your background! It is great to learn about your journey. "
                    f"Now, let us dive directly into your technical assessment on {session.technical_domain}. "
                    f"Here is your first technical question."
                )
                correct_concepts = ["Structured self-introduction", "Clear verbal articulation", "Academic & technical background"]
                missing_concepts = []
                incorrect_statements = []
                explanation = "[DEMO MODE: Rule-based local evaluation] Good self-introduction delivered with clear communication."
                suggestions = "Keep your introduction concise (around 60 to 90 seconds) and highlight your strongest practical projects."
                better_answer = f"Clear professional summary highlighting education, experience in {session.technical_domain}, and technical enthusiasm."
                follow_up_needed = False
                suggested_follow_up = ""

            return {
                'score': score,
                'classification': classification,
                'correct_concepts': correct_concepts,
                'missing_concepts': missing_concepts,
                'incorrect_statements': incorrect_statements,
                'explanation': explanation,
                'suggestions': suggestions,
                'better_answer_example': better_answer,
                'interviewer_response': interviewer_response,
                'follow_up_needed': follow_up_needed,
                'suggested_follow_up': suggested_follow_up,
                'confidence_score': 0.95,
                'ai_mode_used': 'demo'
            }

        target_concept = question.target_concept.lower()
        key_terms = [w.strip() for w in re.split(r'[,;/\s]+', target_concept) if len(w.strip()) > 3]

        matched_terms = [term for term in key_terms if term in text_lower]
        missing_terms = [term for term in key_terms if term not in text_lower]

        if is_idk:
            classification = 'Unable to evaluate'
            score = 10.0
            interviewer_response = (
                "That's honest. In an interview, it's completely acceptable to acknowledge when you don't recall a term. "
                "Can you try reasoning about the basic principle, or should we examine it from another angle?"
            )
            correct_concepts = []
            missing_concepts = [question.target_concept] if question.target_concept else ["Core conceptual answer"]
            incorrect_statements = []
            explanation = "[DEMO MODE: Rule-based local evaluation] Candidate stated uncertainty. Recommended to attempt reasoning from fundamentals."
            suggestions = "Even when uncertain, explain what you know about related concepts and discuss trade-offs."
            better_answer = f"A solid approach begins by breaking down the definition: {question.target_concept}."
            follow_up_needed = True
            suggested_follow_up = f"Let's simplify: What do you think happens initially when we examine {question.target_concept.split(';')[0]}?"

        elif word_count < 10:
            classification = 'Vague'
            score = 40.0
            interviewer_response = "Can you expand on that with a more concrete explanation or practical example?"
            correct_concepts = matched_terms[:1]
            missing_concepts = missing_terms[:3]
            incorrect_statements = []
            explanation = "[DEMO MODE: Rule-based local evaluation] The response is too brief to demonstrate full conceptual mastery."
            suggestions = "Elaborate your reasoning. State definitions, advantages, and real-world examples."
            better_answer = f"A comprehensive answer would detail: {question.target_concept}."
            follow_up_needed = True
            suggested_follow_up = "Could you give me a specific scenario or walk through how that works?"

        elif len(matched_terms) >= max(2, len(key_terms) // 2) or word_count >= 50:
            classification = 'Correct' if len(matched_terms) >= len(key_terms) * 0.7 else 'Mostly correct'
            score = 92.0 if classification == 'Correct' else 80.0
            interviewer_response = (
                "Good explanation. You touched on the core mechanism accurately. "
                "Let's see how that applies in practice."
            )
            correct_concepts = matched_terms if matched_terms else ["Solid conceptual explanation provided"]
            missing_concepts = missing_terms[:2] if missing_terms else []
            incorrect_statements = []
            explanation = "[DEMO MODE: Rule-based local evaluation] Good articulation of essential concepts matching the question requirements."
            suggestions = "To make this even stronger, mention edge cases and space/time trade-offs."
            better_answer = f"Strong answer addressing: {question.target_concept} with clear structure."
            follow_up_needed = False
            suggested_follow_up = ""

        elif len(matched_terms) > 0 or word_count >= 25:
            classification = 'Partially correct'
            score = 62.0
            interviewer_response = "That's partially right. You identified part of the concept, but what about the rest of the mechanism?"
            correct_concepts = matched_terms if matched_terms else ["Basic premise identified"]
            missing_concepts = missing_terms[:3] if missing_terms else ["Deeper trade-offs and mechanics"]
            incorrect_statements = []
            explanation = "[DEMO MODE: Rule-based local evaluation] Key parts of the solution were mentioned, but critical aspects were omitted."
            suggestions = "Ensure you answer both parts of the question, especially performance implications."
            better_answer = f"A complete answer explicitly covers: {question.target_concept}."
            follow_up_needed = True
            suggested_follow_up = "What are the trade-offs or key limitations of that approach?"

        else:
            classification = 'Needs clarification'
            score = 45.0
            interviewer_response = "I'm not fully following your line of reasoning. Can you clarify how that connects to the question?"
            correct_concepts = []
            missing_concepts = [question.target_concept]
            incorrect_statements = ["Answer lacks clear technical alignment with the target question."]
            explanation = "[DEMO MODE: Rule-based local evaluation] The answer diverged from the primary technical topic."
            suggestions = "Focus directly on the question prompts and avoid extraneous details."
            better_answer = f"Focus on: {question.target_concept}."
            follow_up_needed = True
            suggested_follow_up = "Let's focus on the core: how does the system manage this under the hood?"

        return {
            'score': score,
            'classification': classification,
            'correct_concepts': correct_concepts,
            'missing_concepts': missing_concepts,
            'incorrect_statements': incorrect_statements,
            'explanation': explanation,
            'suggestions': suggestions,
            'better_answer_example': better_answer,
            'interviewer_response': interviewer_response,
            'follow_up_needed': follow_up_needed,
            'suggested_follow_up': suggested_follow_up,
            'confidence_score': 0.90,
            'ai_mode_used': 'demo'
        }

    def generate_next_question(self, session, conversation_history: List[Dict], previous_evaluations: List[Dict]) -> Dict[str, Any]:
        """Generates next sequential question from local bank, avoiding duplicates and adapting difficulty."""
        domain = session.technical_domain if session.interview_type != 'HR Interview' else 'HR Interview'
        current_diff = session.current_difficulty

        # Adaptive difficulty logic
        if session.difficulty == 'Adaptive' and previous_evaluations:
            last_score = previous_evaluations[-1].get('score', 60.0)
            if last_score >= 80.0:
                if current_diff == 'Easy':
                    current_diff = 'Medium'
                elif current_diff == 'Medium':
                    current_diff = 'Hard'
            elif last_score < 50.0:
                if current_diff == 'Hard':
                    current_diff = 'Medium'
                elif current_diff == 'Medium':
                    current_diff = 'Easy'
            session.current_difficulty = current_diff
            session.save(update_fields=['current_difficulty'])

        # Gather already asked questions to prevent repetition
        asked_texts = {h.get('question_text', '').strip().lower() for h in conversation_history}

        # Find questions in domain for current difficulty
        domain_dict = DOMAIN_QUESTION_BANKS.get(domain, {})
        candidate_pool = domain_dict.get(current_diff, [])
        # Fallback to other difficulties if exhausted
        if not candidate_pool or all(q['text'].lower() in asked_texts for q in candidate_pool):
            for d in ['Medium', 'Easy', 'Hard']:
                candidate_pool = domain_dict.get(d, [])
                if any(q['text'].lower() not in asked_texts for q in candidate_pool):
                    break

        unasked = [q for q in candidate_pool if q['text'].lower() not in asked_texts]
        if not unasked:
            unasked = [q for q in GENERIC_TECHNICAL_QUESTIONS if q['text'].lower() not in asked_texts]

        if not unasked:
            # Fallback if all bank questions consumed
            q = {
                'text': f"Regarding your experience with {session.technical_domain}, what has been the most challenging technical bug you resolved?",
                'target_concept': 'Systematic debugging and problem resolution',
                'category': 'Practical Engineering',
                'difficulty': current_diff
            }
        else:
            q = unasked[0]

        return {
            'text': q['text'],
            'target_concept': q['target_concept'],
            'category': q['category'],
            'difficulty': current_diff,
            'interviewer_note': f"[DEMO MODE: Deterministic question based on domain '{domain}' at '{current_diff}' difficulty]"
        }

    def generate_final_report(self, session, full_transcript: List[Dict], evaluations: List[Dict]) -> Dict[str, Any]:
        """Constructs a deterministic structured final report."""
        from interviews.services.evaluation_service import EvaluationService
        metrics = EvaluationService.calculate_session_metrics(evaluations)

        score = metrics.get('overall_score') or 0.0

        if score >= 85:
            summary = "Outstanding technical readiness. Demonstrated solid conceptual depth and structured reasoning across all key topics."
            next_step = "Practice advanced system design or complex algorithm optimization to prepare for top-tier product companies."
        elif score >= 70:
            summary = "Competent baseline performance with good fundamentals. Some answers missed secondary nuances or edge-case handling."
            next_step = "Focus on reinforcing edge cases, time/space trade-offs, and practical architecture patterns."
        elif score >= 50:
            summary = "Moderate grasp of core topics. Several answers were partially complete or required follow-up clarification."
            next_step = "Review standard textbook implementations and practice explaining concepts out loud without hesitation."
        else:
            summary = "Needs foundational revision across fundamental topics. Key concepts were either missing or confused."
            next_step = "Revisit fundamental data structures, database principles, and practice mock interviews frequently."

        return {
            'overall_score': score,
            'performance_summary': summary,
            'strengths': metrics.get('strengths') or [f"Basic familiarity with {session.technical_domain}"],
            'knowledge_gaps': metrics.get('knowledge_gaps') or ["In-depth mechanism explanations and trade-offs"],
            'recommended_topics': metrics.get('recommended_topics') or [f"{session.technical_domain} Fundamentals"],
            'communication_feedback': "Ensure answers follow a clear problem-action-result structure. Keep pauses natural and avoid over-apologizing.",
            'suggested_next_practice': next_step,
            'ai_mode_used': 'demo',
            'disclaimer': "[DEMO MODE REPORT: Calculated deterministically via local scoring rubric. Connect an AI API key in .env for generative LLM assessments.]"
        }


class OpenAIAIService(BaseAIService):
    """
    Real AI service using OpenAI or OpenAI-compatible endpoint (e.g. Groq, Ollama, DeepSeek).
    """

    def __init__(self, api_key: str, model: str = 'gpt-4o-mini', base_url: Optional[str] = None, timeout: int = 25):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url if base_url else None
        self.timeout = timeout

        try:
            from openai import OpenAI
            kwargs = {'api_key': self.api_key, 'timeout': self.timeout}
            if self.base_url:
                kwargs['base_url'] = self.base_url
            self.client = OpenAI(**kwargs)
        except Exception as e:
            logger.error("Failed to initialize OpenAI client: %s", e)
            self.client = None

    def _call_llm_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        if not self.client:
            raise RuntimeError("OpenAI client not initialized.")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt + "\nYou must reply strictly with a valid JSON object. Do not output markdown code blocks or extra text."},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.4,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response received from LLM.")

        # Clean potential markdown wrapping
        content = re.sub(r'^```json\s*', '', content.strip(), flags=re.MULTILINE)
        content = re.sub(r'```$', '', content.strip(), flags=re.MULTILINE)
        return json.loads(content)

    def generate_first_question(self, session) -> Dict[str, Any]:
        system_prompt = (
            "You are a rigorous, professional technical interviewer conducting a campus placement interview for engineering students.\n"
            "This is the opening of the interview: warmly welcome the candidate, introduce yourself, and ask them to introduce themselves, "
            "share their academic background, and describe what technologies or projects they enjoy working on.\n"
            "Respond strictly in JSON with fields: 'text', 'target_concept', 'category', 'difficulty', 'interviewer_note'."
        )
        user_prompt = (
            f"Interview Type: {session.interview_type}\n"
            f"Technical Domain: {session.technical_domain}\n"
            f"Difficulty: {session.difficulty}\n"
            f"Experience Level: {session.experience_level}\n"
            f"Target Role: {session.target_role or 'General Engineering'}\n"
            f"Job Description: {session.job_description or 'Standard entry-level software engineering'}\n"
            f"Candidate Skills: {session.skills or 'Core computer science fundamentals'}"
        )
        try:
            data = self._call_llm_json(system_prompt, user_prompt)
            data['interviewer_note'] = f"[Real AI Mode: {self.model}]"
            return data
        except Exception as e:
            logger.warning("OpenAI error in generate_first_question: %s. Falling back to Demo mode.", e)
            fallback = DemoAIService().generate_first_question(session)
            fallback['interviewer_note'] = f"[Real AI provider temporarily unreachable ({e}). Fallback to local question]"
            return fallback

    def evaluate_answer(self, session, question, answer_text: str, conversation_history: List[Dict]) -> Dict[str, Any]:
        system_prompt = (
            "You are an expert technical interviewer evaluating an engineering candidate's placement interview answer.\n"
            "Evaluate realistically: allow valid alternative explanations, do not praise every response, distinguish between minor omissions and factual blunders.\n"
            "Return strictly a JSON object with keys:\n"
            "- 'score': number from 0 to 100 based on technical correctness (40%), conceptual depth (25%), completeness (20%), practical reasoning (15%)\n"
            "- 'classification': one of ['Correct', 'Mostly correct', 'Partially correct', 'Incorrect', 'Vague', 'Off-topic', 'Needs clarification', 'Unable to evaluate']\n"
            "- 'correct_concepts': list of strings\n"
            "- 'missing_concepts': list of strings\n"
            "- 'incorrect_statements': list of strings\n"
            "- 'explanation': string explaining mistakes concisely\n"
            "- 'suggestions': actionable improvement tips\n"
            "- 'better_answer_example': concise example of an exemplary answer\n"
            "- 'interviewer_response': professional spoken response to candidate (e.g. 'That is partially correct. What happens when...')\n"
            "- 'follow_up_needed': boolean\n"
            "- 'suggested_follow_up': string (if follow_up_needed is true, provide the exact question to ask next)\n"
            "- 'confidence_score': float between 0.0 and 1.0"
        )
        user_prompt = (
            f"Domain: {session.technical_domain}\n"
            f"Question Asked: {question.text}\n"
            f"Target Concept: {question.target_concept}\n"
            f"Candidate's Answer: {answer_text}\n"
            f"Language: {session.interview_language}"
        )
        try:
            data = self._call_llm_json(system_prompt, user_prompt)
            data['ai_mode_used'] = f"openai ({self.model})"
            return data
        except Exception as e:
            logger.warning("OpenAI error in evaluate_answer: %s. Falling back to Demo mode.", e)
            fallback = DemoAIService().evaluate_answer(session, question, answer_text, conversation_history)
            fallback['explanation'] = f"[AI Provider Unavailable: {e}. Fallback evaluation used.]\n" + fallback.get('explanation', '')
            return fallback

    def generate_next_question(self, session, conversation_history: List[Dict], previous_evaluations: List[Dict]) -> Dict[str, Any]:
        system_prompt = (
            "You are an AI technical interviewer. Generate the next question in the placement interview sequence.\n"
            "Review past questions to NEVER repeat a topic. Adapt difficulty if candidate performed well or struggled.\n"
            "Respond strictly in JSON with keys: 'text', 'target_concept', 'category', 'difficulty', 'interviewer_note'."
        )
        user_prompt = (
            f"Domain: {session.technical_domain}\n"
            f"Current Difficulty: {session.current_difficulty}\n"
            f"Interview Type: {session.interview_type}\n"
            f"Candidate Experience: {session.experience_level}\n"
            f"Previous questions count: {len(conversation_history)}\n"
            f"History summary: {json.dumps(conversation_history[-4:] if conversation_history else [])}"
        )
        try:
            data = self._call_llm_json(system_prompt, user_prompt)
            data['interviewer_note'] = f"[Real AI Mode: {self.model}]"
            return data
        except Exception as e:
            logger.warning("OpenAI error in generate_next_question: %s. Falling back to Demo mode.", e)
            return DemoAIService().generate_next_question(session, conversation_history, previous_evaluations)

    def generate_final_report(self, session, full_transcript: List[Dict], evaluations: List[Dict]) -> Dict[str, Any]:
        system_prompt = (
            "You are a Senior Technical Hiring Manager generating a comprehensive post-interview feedback report for an engineering student.\n"
            "Provide objective, actionable, encouraging yet honest feedback based solely on the interview transcript.\n"
            "Respond strictly in JSON with keys:\n"
            "- 'overall_score': float 0-100\n"
            "- 'performance_summary': string\n"
            "- 'strengths': list of strings\n"
            "- 'knowledge_gaps': list of strings\n"
            "- 'recommended_topics': list of strings\n"
            "- 'communication_feedback': string\n"
            "- 'suggested_next_practice': string"
        )
        user_prompt = (
            f"Interview Session: {session.title}\n"
            f"Domain: {session.technical_domain}\n"
            f"Experience: {session.experience_level}\n"
            f"Transcript & Evaluations: {json.dumps(evaluations)}"
        )
        try:
            data = self._call_llm_json(system_prompt, user_prompt)
            data['ai_mode_used'] = f"openai ({self.model})"
            data['disclaimer'] = f"[Evaluated via {self.model} with automated rubric benchmarks]"
            return data
        except Exception as e:
            logger.warning("OpenAI error in generate_final_report: %s. Falling back to Demo mode.", e)
            return DemoAIService().generate_final_report(session, full_transcript, evaluations)


class GeminiAIService(BaseAIService):
    """
    Direct REST Gemini API implementation using requests.
    Supports official Google Gemini API (gemini-1.5-flash / gemini-2.0-flash / etc.) via REST.
    """

    def __init__(self, api_key: str, model: str = 'gemini-1.5-flash', timeout: int = 25):
        self.api_key = api_key
        self.model = model or 'gemini-1.5-flash'
        self.timeout = timeout
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

    def _call_gemini_json(self, prompt: str) -> Dict[str, Any]:
        import requests
        headers = {'Content-Type': 'application/json'}
        body = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt + "\nOutput strictly valid JSON only. Do not surround with markdown backticks."}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.4,
                "responseMimeType": "application/json"
            }
        }
        res = requests.post(self.endpoint, json=body, headers=headers, timeout=self.timeout)
        if res.status_code != 200:
            raise RuntimeError(f"Gemini API returned status {res.status_code}: {res.text}")

        data = res.json()
        candidates = data.get('candidates', [])
        if not candidates:
            raise ValueError("No candidates returned from Gemini API.")

        text = candidates[0]['content']['parts'][0]['text']
        cleaned = re.sub(r'^```json\s*', '', text.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r'```$', '', cleaned.strip(), flags=re.MULTILINE)
        return json.loads(cleaned)

    def generate_first_question(self, session) -> Dict[str, Any]:
        prompt = (
            f"You are a technical interviewer for campus placements.\n"
            f"Generate an opening question welcoming the candidate to their {session.technical_domain} interview, "
            f"introducing yourself, and asking them to introduce themselves, their academic background, and projects they enjoy.\n"
            f"Output JSON with keys: text, target_concept, category, difficulty, interviewer_note."
        )
        try:
            data = self._call_gemini_json(prompt)
            data['interviewer_note'] = f"[Real AI Mode: Gemini {self.model}]"
            return data
        except Exception as e:
            logger.warning("Gemini error in generate_first_question: %s. Falling back to Demo mode.", e)
            return DemoAIService().generate_first_question(session)

    def evaluate_answer(self, session, question, answer_text: str, conversation_history: List[Dict]) -> Dict[str, Any]:
        prompt = (
            f"Evaluate candidate answer for technical placement interview.\n"
            f"Question: {question.text}\nConcept: {question.target_concept}\nCandidate Answer: {answer_text}\n"
            f"Return JSON with: score (0-100), classification ('Correct'/'Mostly correct'/'Partially correct'/'Incorrect'/'Vague'/'Off-topic'/'Needs clarification'/'Unable to evaluate'), "
            f"correct_concepts (list), missing_concepts (list), incorrect_statements (list), explanation, suggestions, better_answer_example, interviewer_response, follow_up_needed (bool), suggested_follow_up, confidence_score (float)."
        )
        try:
            data = self._call_gemini_json(prompt)
            data['ai_mode_used'] = f"gemini ({self.model})"
            return data
        except Exception as e:
            logger.warning("Gemini error in evaluate_answer: %s. Falling back to Demo mode.", e)
            return DemoAIService().evaluate_answer(session, question, answer_text, conversation_history)

    def generate_next_question(self, session, conversation_history: List[Dict], previous_evaluations: List[Dict]) -> Dict[str, Any]:
        prompt = (
            f"Generate next question in technical interview.\nDomain: {session.technical_domain}, Current Difficulty: {session.current_difficulty}.\n"
            f"Previous questions count: {len(conversation_history)}.\n"
            f"Return JSON with: text, target_concept, category, difficulty, interviewer_note."
        )
        try:
            data = self._call_gemini_json(prompt)
            data['interviewer_note'] = f"[Real AI Mode: Gemini {self.model}]"
            return data
        except Exception as e:
            logger.warning("Gemini error in generate_next_question: %s. Falling back to Demo mode.", e)
            return DemoAIService().generate_next_question(session, conversation_history, previous_evaluations)

    def generate_final_report(self, session, full_transcript: List[Dict], evaluations: List[Dict]) -> Dict[str, Any]:
        prompt = (
            f"Generate final placement interview report.\nDomain: {session.technical_domain}.\n"
            f"Evaluations: {json.dumps(evaluations)}.\n"
            f"Return JSON with: overall_score (0-100), performance_summary, strengths (list), knowledge_gaps (list), recommended_topics (list), communication_feedback, suggested_next_practice."
        )
        try:
            data = self._call_gemini_json(prompt)
            data['ai_mode_used'] = f"gemini ({self.model})"
            data['disclaimer'] = f"[Evaluated via Gemini {self.model} with automated rubric benchmarks]"
            return data
        except Exception as e:
            logger.warning("Gemini error in generate_final_report: %s. Falling back to Demo mode.", e)
            return DemoAIService().generate_final_report(session, full_transcript, evaluations)


def get_ai_service() -> BaseAIService:
    """
    Factory function returning the configured AI service instance.
    Checks environment settings:
    - If AI_PROVIDER == 'demo' or AI_API_KEY is missing/empty, returns DemoAIService.
    - If AI_PROVIDER in ('openai', 'custom') and AI_API_KEY is provided, returns OpenAIAIService.
    - If AI_PROVIDER == 'gemini' and AI_API_KEY is provided, returns GeminiAIService.
    """
    provider = getattr(settings, 'AI_PROVIDER', 'demo').lower()
    api_key = getattr(settings, 'AI_API_KEY', '').strip()
    model = getattr(settings, 'AI_MODEL', 'gpt-4o-mini').strip()
    api_base = getattr(settings, 'AI_API_BASE', '').strip()
    timeout = getattr(settings, 'AI_TIMEOUT_SECONDS', 25)

    if not api_key or provider == 'demo':
        return DemoAIService()

    if provider in ('openai', 'custom'):
        return OpenAIAIService(api_key=api_key, model=model, base_url=api_base or None, timeout=timeout)

    if provider == 'gemini':
        return GeminiAIService(api_key=api_key, model=model, timeout=timeout)

    # Fallback to demo service
    return DemoAIService()


def get_ai_service_status() -> Dict[str, Any]:
    """Provides provider status information for templates and UI banners."""
    provider = getattr(settings, 'AI_PROVIDER', 'demo').lower()
    api_key = getattr(settings, 'AI_API_KEY', '').strip()
    model = getattr(settings, 'AI_MODEL', 'gpt-4o-mini').strip()

    is_real = bool(api_key and provider != 'demo')
    return {
        'is_real_ai': is_real,
        'provider_name': provider if is_real else 'demo',
        'model_name': model if is_real else 'Deterministic Local Engine',
        'status_label': f"Active ({provider.upper()} - {model})" if is_real else "Demo Mode (Rule-based local evaluation)",
        'badge_class': 'badge-success' if is_real else 'badge-warning'
    }
