from pathlib import Path
from typing import Callable, Optional, NamedTuple, List, Tuple, Pattern, Dict, Any
from enum import Enum
from subprocess import Popen, PIPE
import re

from powerline.theme import requires_segment_info
from powerline.segments import Segment, with_docstring


BRANCH_HEAD_REGEX = re.compile('#.+ ([\w/]+)$')
BRANCH_UPSTREAM_REGEX = BRANCH_HEAD_REGEX
BRANCH_AB_REGEX = re.compile('#.+ \+(\d) -(\d)$')
BRANCH_STAGED_REGEX = re.compile('\w\.')
BRANCH_UNSTAGED_REGEX = re.compile('\.\w')
GIT_STATUS_CMD = ['git', 'status', '--porcelain=v2', '--branch', '--ignored']
GIT_STASH_CMD1 = ['git', 'stash', 'list']

COLORS = {
    'gitstatus': {
        'clean': ['branch:clean'],
        'dirty': ['branch:dirty'],
        'broken': ['branch:broken'],
        'default': ['branch:clean'],
    },
    'branch': ['branch:name'],
    'files': ['files:info'],
    'stash': ['files:info'],
    'red': ['battery_full'],
}


Seg = Dict[str, Any]


class GitStatus(Enum):
    CLEAN = 1
    DIRTY = 2
    BROKEN = 3

    def segment(self) -> Seg:
        contents = ''
        highlight_groups = []
        if self == GitStatus.CLEAN:
            contents = '✔'
            highlight_groups = COLORS['gitstatus']['clean']
        elif self == GitStatus.DIRTY:
            contents = '⨀ '
            highlight_groups = COLORS['gitstatus']['dirty']
        elif self == GitStatus.BROKEN:
            contents = '✘'
            highlight_groups = COLORS['gitstatus']['broken']
        else:
            contents = '⁉'
            highlight_groups = COLORS['gitstatus']['default']

        return {
            'contents': contents,
            'highlight_groups': highlight_groups,
            'draw_inner_divider': True
        }

class Branch(NamedTuple):
    head: str
    upstream: Optional[str]
    ahead: Optional[int]
    behind: Optional[int]


class GitRepo(NamedTuple):
    branch: Branch
    staged: List[Path]
    unstaged: List[Path]
    untracked: List[Path]
    ignored: List[Path]
    stashed: int
    status: GitStatus

    def files_segment(self) -> Optional[Seg]:
        files_info = []
        if self.staged:
            files_info.append('⚫{}'.format(len(self.staged)))
        if self.staged:
            files_info.append('{}'.format(len(self.staged)))
        if self.unstaged:
            files_info.append('±{}'.format(len(self.unstaged)))
        if self.untracked: 
            files_info.append('…{}'.format(len(self.untracked)))
        return {
            'contents': '╱'.join(files_info),
            'draw_inner_divider': True,
            'highlight_groups': COLORS['files']
        }

    def branch_segment(self) -> Optional[Seg]:
        contents = '{}'.format(self.branch.head)
        return {
            'contents': contents,
            'draw_inner_divider': True,
            'highlight_groups': COLORS['branch']
        }

    def status_segment(self) -> Optional[Seg]:
        return self.status.segment()

    def stash_segment(self) -> Optional[Seg]:
        if self.stashed:
            return {
                'contents': '⚑{}'.format(self.stashed),
                'draw_inner_divider': True,
                'highlight_groups' : COLORS['stash']
            }
        return None

    def red_segment(self) -> Optional[Seg]:
        return {
            'contents': '☭',
            'highlight_groups': COLORS['red']
        }


class ParseError(Exception):
    pass


class BranchParseError(Exception):
    pass


def capture(regex: Pattern, value: str, min_items: int = 1) -> List[str]:
    match = regex.match(value)
    if not match or len(match.groups()) < min_items:
        raise ParseError('Error: "{}" capturing "{}" [{}]'.format(regex.pattern, value, min_items))
    return list(match.groups())


def parse_branch_data(data: List[str]) -> Tuple[List[str], Branch]:
    if not data:
        raise BranchParseError()
    new_data = []
    head = None  # type: Optional[str]
    upstream = None  # type: Optional[str]
    ahead = None  # type: Optional[int]
    behind = None  # type: Optional[int]
    for line in data:
        if line.startswith('#'):
            _, branch_prefix, *branch_data = line.split(' ')
            if branch_prefix == 'branch.head':
                head = branch_data[0]
            elif branch_prefix == 'branch.upstream':
                upstream = branch_data[0]
            elif branch_prefix == 'branch.ab':
                ahead, behind = [int(i[1:]) for i in branch_data]
        else:
            new_data.append(line)

    if head is None:
        raise BranchParseError()

    return new_data, Branch(head = head, upstream = upstream, ahead = ahead,
                            behind = behind)


def parse_staged_files_data(data: List[str]) -> Tuple[List[str], List[Path], List[Path]]:
    new_data = []  # type: List[str]
    staged_files = []  # type: List[Path]
    unstaged_files = []  # type: List[Path]
    for line in data:
        if line.startswith('1'):
            staged_info = line.split()
            if BRANCH_STAGED_REGEX.match(staged_info[1]):
                staged_files.append(Path(staged_info[8]))
            else:
                unstaged_files.append(Path(staged_info[8]))
        else:
            new_data.append(line)

    return new_data, staged_files, unstaged_files


def parse_untracked_files_data(data: List[str]) -> Tuple[List[str], List[Path]]:
    new_data = []  # type: List[str]
    untracked_files = []  # type: List[Path]
    for line in data:
        if line.startswith('?'):
           untracked_files.append(Path(line.split()[1]))
        else:
            new_data.append(line)

    return new_data, untracked_files


def parse_ignored_files_data(data: List[str]) -> Tuple[List[str], List[Path]]:
    new_data = []  # type: List[str]
    ignored_files = []  # type: List[Path]
    for line in data:
        if line.startswith('!'):
            ignored_files.append(Path(line.split()[1]))
        else:
            new_data.append(line)

    return new_data, ignored_files


def parse_git_status(data_str: str, stash_data_str: str) -> GitRepo:
    data, branch = parse_branch_data(data_str.split('\n'))
    data, staged, unstaged = parse_staged_files_data(data)
    data, untracked = parse_untracked_files_data(data)
    data, ignored = parse_ignored_files_data(data)
    stashed = len(stash_data_str.split('\n')) - 1
    
    if len(staged) == 0 and len(unstaged) == 0:
        status = GitStatus.CLEAN
    else:
        status = GitStatus.DIRTY

    return GitRepo(branch = branch, staged = staged, unstaged = unstaged, ignored = ignored,
                   untracked = untracked, status=status, stashed=stashed)


def git_from_path(path: Path) -> Optional['GitRepo']:
    if not path.exists():
        return None

    p1 = Popen(GIT_STATUS_CMD, cwd=str(path), stdout=PIPE, stderr=PIPE)
    out1, _ = p1.communicate()
    if p1.returncode > 0:
        return None

    p2 = Popen(GIT_STASH_CMD1, cwd=str(path), stdout=PIPE, stderr=PIPE)
    out2, _ = p2.communicate()
    if p2.returncode > 0:
        return None

    return parse_git_status(out1.decode(), out2.decode())


@requires_segment_info
class GitSegment(Segment):
    def __call__(self, pl, segment_info, **kwargs) -> List[Seg]:
        segments = []  # type: List[Optional[Seg]]
        args = segment_info['args']
        pane_id = args.renderer_arg.get('pane_id')
        if pane_id is None:
            pl.debug('No found pane_id in %s' % segment_info['args'].renderer_arg)
            return []
        environ = segment_info['environ']
        path = environ.get('TMUX_PWD_{}'.format(pane_id))
        if not path:
            pl.debug('No found path in %s for pane_id %s' % ([[e,v] for e, v in environ.items() if e.startswith('TMUX_PWD')], pane_id))
            return []
        pl.debug('PWD is %s and pane is %s' % (path, pane_id))
        git = git_from_path(Path(segment_info['getcwd']()))

        if git:
            segments = [
                git.branch_segment(),
                git.status_segment(),
                git.stash_segment(),
                git.files_segment(),
                git.red_segment(),
            ]
            pl.debug('Segments are %s' % segments)
            return [s for s in segments if s]
        return []


git = with_docstring(GitSegment(),
'''
''')

