import logging

from copy import deepcopy
from rich import print




class Transition:
    def __init__(self, on, source, dest):
        self.on = on
        self.source = source
        self.dest = dest

    @staticmethod
    def node_str(node):
        return f"{node}"

    def __repr__(self):
        return f"{self.node_str(self.source)} --('{self.on}')--> {self.node_str(self.dest)}"

class FiniteAutomaton:

    def copy(self):
        return deepcopy(self)

    def max_node(self):
        return max((max(t.source,t.dest) for t in self.transitions))

    def min_node(self):
        return min((min(t.source,t.dest) for t in self.transitions))

    def __repr__(self):
        t_strings = "\n".join(
            (f"{t}" for t in sorted(self.transitions, key=lambda t: t.source))
        )

        return f"START: {self.start}   TERM: {self.term}\n{t_strings}"

    def to_graphviz(self, title=""):
        t_strings = "\n".join(
            (f"{t.source} -> {t.dest} [ label = \"{t.on if t.on else 'ε'}\" ];" for t in self.transitions)
        )

        if hasattr(self.term, '__iter__'):
            term_string = ' '.join((f'{n}' for n in self.term))
        else:
            term_string = f'{self.term}'

        return (
            f'digraph finite_state_machine {{\n'
            f'labelloc="t";'
            f'label="{title}";'
            f'    rankdir=LR;\n'
            f'    size="8,5"\n'
            f'    node [shape = doublecircle]; {self.start} {term_string};\n'
            f'    node [shape = circle];\n'
            f'    {t_strings}\n'
            f'}}'
        )

class DFA(FiniteAutomaton):
    """Deterministic finite automoton"""
    def __init__(self, transitions=None, start=-1, term=None):
        self.transitions = transitions or []
        self.start = start
        self.term = term or []
    

class NFA(FiniteAutomaton):
    """Nondeterministic finite automoton"""
    def __init__(self, transitions=None, start=-1, term=-1):
        self.transitions = transitions or []
        self.start = start
        self.term = term

    def to_dfa(self):
        new_states = []
        new_transitions = []
        new_term_states = []
        queue = []

        new_initial_state = self.epsilon_closure((self.start,))
        new_states.append(new_initial_state)
        queue.append(new_initial_state)

        while queue:
            current_state = queue.pop()
            for current_on in self.get_moves_for_nodes(current_state):
                if current_on == '':
                    continue

                possibly_new_state = self.epsilon_closure(self.move_on(current_state, current_on))
                if possibly_new_state not in new_states:
                    queue.append(possibly_new_state)
                    new_states.append(possibly_new_state)

                    if self.term in possibly_new_state:
                        new_term_states.append(len(new_states)-1)

                new_transitions.append(
                    Transition(
                        source=new_states.index(current_state),
                        dest=new_states.index(possibly_new_state),
                        on=current_on
                    )
                )

        # for i, s in enumerate(new_states):
        #     print(f"{i}: {s}")

        return DFA(new_transitions, 0, new_term_states)
        # start + epsilon closure  ==> new initial state, add to stack
        # pop state off stack and for each possible char in "transition on" set, get
        #   epsilon closure of (all states after transition on that char)
        #   ==> state identified by set of old states
        # repeat until nothing in stack

    def nodes(self):
        return sorted(list( {t.start for t in self.transitions} + {t.term for t in self.transitions} ))

    def transitions_from(self, nodes):
        return [t for t in self.transitions if t.source in nodes]

    def get_moves_for_nodes(self, nodes):
        return sorted(list({t.on for t in self.transitions if t.source in nodes}))

    def epsilon_closure(self, nodes):
        fixed_point = [n for n in nodes]
        new_eps = self.move_on(nodes, '')
        while new_eps:
            fixed_point.extend(new_eps)
            new_eps = set(self.move_on(new_eps, '')) - set(fixed_point)

        return fixed_point

    def move_on(self, nodes, on):
        move_on = []
        for t in self.transitions:
            if t.on == on and t.source in nodes:
                move_on.append(t.dest)

        return sorted(move_on)

    def closure(self, nodes, on):
        extra_nodes = set()
        for t in self.transitions:
            if transition.on == on and transition.source in nodes:
                extra_nodes.add(transition.dest)

        return sorted(list(set(nodes) + extra_nodes))



    def prepend_new_start(self):
        new_start = self.min_node()
        self.add_offset(1)
        self.transitions.append(
            Transition('', new_start, self.start)
        )

        self.start = new_start

    def append_new_term(self):
        new_term = self.max_node() + 1
        old_term = self.term

        self.transitions.append(
            Transition('', old_term, new_term)
        )

        self.term = new_term

    def add_offset(self, offset):
        self.start += offset
        self.term += offset
        for t in self.transitions:
            t.source += offset
            t.dest += offset

    def replace_node(self, orig, new):
        for t in self.transitions:
            if t.source == orig:
                t.source = new
            if t.dest == orig:
                t.dest = new

    @classmethod
    def from_char(cls, char):
        return cls([Transition(char, 0, 1)], 0, 1)

    def concat(self, right):
        offset = self.max_node()
        if offset != self.term:
            offset += 1

        right.add_offset(offset)
        right.replace_node(self.start, offset)

        self.replace_node(self.term, offset)
        self.term = right.term

        self.transitions.extend(right.transitions)

        return self

    def disjunct(self, disjunct):
        self.prepend_new_start()
        new_start = self.start

        old_term = self.term
        self.append_new_term()
        new_term = self.term

        offset = new_term + 1

        disjunct.add_offset(offset)

        self.transitions.append(
            Transition('', new_start, disjunct.start)
            )
        
        self.transitions.append(
            Transition('', disjunct.term, new_term)
            )

        self.transitions.extend(disjunct.transitions)

        return self

    def zero_or_more(self):
        self.transitions.append(
            Transition('', self.start, self.term)
            )
        self.transitions.append(
            Transition('', self.term, self.start)
            )

        self.append_new_term()

        return self



class RegexString:
    def __init__(self, s):
        self.s = s
        self.i = 0

    def pop(self):
        if self.is_eof():
            return ""

        c = self.s[self.i]
        self.i += 1
        return c

    def pop_if(self, c):
        if self.peek() == c:
            self.pop()
            return True

        return False

    def peek(self):
        if self.is_eof():
            return ""

        return self.s[self.i]

    def is_eof(self):
        return self.i == len(self.s)

    def push_back(self):
        self.i -= 1

    def parse(self):
        return RegDisj.from_buf(self)


class RegUnity:
    """Char or Group"""
    def __init__(self, child):
        logging.debug(f"unity --> {child}")
        self.child = child

    @classmethod
    def from_buf(cls, buf):
        if buf.peek() == "(":
            return cls(RegGroup.from_buf(buf))
        else:
            c = RegChar.from_buf(buf)
            if c:
                return cls(c)

            return False

    def to_nfa(self):
        return self.child.to_nfa()

    def __repr__(self):
        # return f"Unity({self.child})"
        return f"{self.child}"


class RegChar:
    """Single character"""
    def __init__(self, child):
        logging.debug(f"char --> {child}")
        self.child = child

    @classmethod
    def from_buf(cls, buf):
        c = buf.pop()
        # print(c)

        if c.isalnum():
            return cls(c)
        else:
            buf.push_back()
            return False

    def to_nfa(self):
        return NFA.from_char(self.child)

    def __repr__(self):
        return f"[bold underline white]{self.child}[/bold underline white]"


class RegGroup:
    """Parentheses (around anything)"""
    def __init__(self, child):
        logging.debug(f"group --> {child}")
        self.child = child

    @classmethod
    def from_buf(cls, buf):
        if buf.pop() == "(":
            exp = RegDisj.from_buf(buf)
            if buf.pop() != ")":
                raise ValueError("no closing ) for group")
            return cls(exp)
        else:
            buf.push_back()
            return False

    def to_nfa(self):
        return self.child.to_nfa()

    def __repr__(self):
        return f"[purple]Group[/purple]( {self.child} )"


class RegQuality:
    """Zero or more unities"""
    def __init__(self, child, qualifier):
        logging.debug(f"quality --> {child}, {qualifier}")
        self.child = child
        self.qualifier = qualifier

    @classmethod
    def from_buf(cls, buf):
        exp = RegUnity.from_buf(buf)

        if not exp:
            return False

        if buf.peek() in ('*', '+'):
            qualifier = buf.pop()
        else:
            qualifier = ''
        return cls(exp, qualifier)
    
    def to_nfa(self):
        child_nfa = self.child.to_nfa()
        if self.qualifier == '':
            return child_nfa
        elif self.qualifier == '*':
            return child_nfa.zero_or_more()
        elif self.qualifier == '+':
            rep_nfa = child_nfa.copy().zero_or_more()
            child_nfa.concat(rep_nfa)

            return child_nfa
        else:
            raise ValueError("Unknown qualifier")

    def __repr__(self):
        if self.qualifier == '':
            return f"{self.child}"
        elif self.qualifier == '*':
            return f"[red]ZeroOrMore[/red]( {self.child} )"
        elif self.qualifier == '+':
            return f"[red]OneOrMore[/red]( {self.child} )"
        else:
            return f"UnknownQualifier( {self.child} )"


class RegConcat:
    """Concatenation of qualities"""
    def __init__(self, children):
        logging.debug(f"concat --> {children}")
        self.children = children

    @classmethod
    def from_buf(cls, buf):
        exps = []
        exp = RegQuality.from_buf(buf)

        while exp:
            exps.append(exp)
            exp = RegQuality.from_buf(buf)

        if exps:
            return cls(exps)

        return False

    def to_nfa(self):
        nfa = self.children[0].to_nfa()

        for child in self.children[1:]:
            nfa.concat(child.to_nfa())

        return nfa

    def __repr__(self):
        if len(self.children) > 1:
            s = ", ".join((f"{c}" for c in self.children))
            return f"[green]Concat[/green]( {s} )"

        return f"{self.children[0]}"


class RegDisj:
    """Disjunction of concats, highest level expression type since trivial disjunction allowed"""
    def __init__(self, children):
        self.children = children

    @classmethod
    def from_buf(cls, buf):
        exps = []
        exp = RegConcat.from_buf(buf)

        while exp:
            exps.append(exp)

            if buf.peek() == "|":
                buf.pop()
                exp = RegConcat.from_buf(buf)
            else:
                break

        if exps:
            return cls(exps)

        return False

    def to_nfa(self):
        nfa = self.children[0].to_nfa()

        for child in self.children[1:]:
            nfa.disjunct(child.to_nfa())

        return nfa

    def __repr__(self):
        if len(self.children) > 1:
            s = ", ".join((f"{c}" for c in self.children))
            return f"[blue]Disjunction[/blue]( {s} )"

        return f"{self.children[0]}"



if __name__ == "__main__":
    strings = ("a(bc|d)*","z+(a|b)","ab*cd*", "a|b", "a|bc", "a|bc+", "a|(bc)+d")
    # strings = ("ab", "ab|cd", "abc*", "(ab)*", "abc+|d")
    # strings = ("a|(bc)+d",)

    for i,s in enumerate(strings):
        parsed = RegexString(s).parse()
        print(f"[bold underline]{s}[/bold underline]  --->  {parsed}")
        print()

        nfa = parsed.to_nfa()
        print(f"[bold]Nondeterministic finite automaton[/bold]")
        print(nfa)
        print()

        dfa = nfa.to_dfa()
        print(f"[bold]Deterministic finite automaton[/bold]")
        print(dfa)
        print()

        with open(f"nfa{i}.gv", "w") as f:
            f.write(nfa.to_graphviz(s))

        with open(f"dfa{i}.gv", "w") as f:
            f.write(dfa.to_graphviz(s))


