import logging
from segments.tmux.git import Branch, parse_branch_data

logging.basicConfig(level=logging.DEBUG)

branch_data_input = [
    """
# branch.oid some_hash
# branch.head master""",
    """
# branch.oid some_hash
# branch.head feature/some_branch""",
    """
# branch.oid some_hash
# branch.head test_repo
# branch.upstream origin/test_repo
# branch.ab +0 -0
1 some content
? some content""",
    """
# branch.oid some_hash
# branch.head test_repo
# branch.upstream origin/test_repo
# branch.ab +0 -100""",
    """
# branch.oid some_hash
# branch.head test_repo
# branch.upstream origin/test_repo
# branch.ab +100 -0""",
    """
# branch.oid some_hash
# branch.head test_repo
# branch.upstream origin/test_repo
# branch.ab +100 -100""",
]

branch_data_expected = [
    (Branch('master', None, None, None), []),
    (Branch('feature/some_branch', None, None, None), []),
    (Branch('test_repo', 'origin/test_repo', 0, 0), [
        '1 some content',
        '? some content'
    ]),
    (Branch('test_repo', 'origin/test_repo', 0, 100), []),
    (Branch('test_repo', 'origin/test_repo', 100, 0), []),
    (Branch('test_repo', 'origin/test_repo', 100, 100), []),
]


def test_parse_branch_data():
    log = logging.getLogger('test_parse_branch_data')
    for i, data in enumerate(branch_data_input):
        log.debug('Testing entry %d' % i)
        rest, branch = parse_branch_data(data.split('\n')[1:])
        assert branch == branch_data_expected[i][0]
        assert rest == branch_data_expected[i][1]
