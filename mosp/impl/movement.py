"""Movement implementation code snippets"""

__author__ = "B. Henne, F. Ludwig, P. Tute"
__contact__ = "henne@dcsec.uni-hannover.de"
__copyright__ = "(c) 2010-2011, DCSec, Leibniz Universitaet Hannover, Germany"
__license__ = "GPLv3"

def person_next_target_random(self):
    """Randomly finds a new next_node to move to.
    
    Ignores the last visited node, if possible without getting stuck.
    Does not set destination_node. Random movement only uses
    last_node and next_node of a Person.
    @author: P. Tute"""
    #possible_targets = self.next_node.n
    possible_targets = sorted(self.next_node.neighbors.keys())
    if len(possible_targets) > 1 and self.last_node in possible_targets:
        possible_targets.remove(self.last_node)
    self.last_node = self.next_node
    self.next_node = self._random.choice(possible_targets)
