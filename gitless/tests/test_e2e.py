# Gitless - a version control system built on top of Git.
# Licensed under GNU GPL v2.

"""End-to-end test."""


import logging
import time
import unittest

import gitless.tests.utils as utils_lib


class TestEndToEnd(utils_lib.TestBase):

  def setUp(self):
    super(TestEndToEnd, self).setUp('gl-e2e-test')
    utils_lib.gl_expect_success('init')
    utils_lib.set_test_config()


# TODO(sperezde): add dialog related tests.
# TODO(sperezde): add checkout related tests.


class TestBasic(TestEndToEnd):

  def test_basic_functionality(self):
    utils_lib.write_file('file1', 'Contents of file1')
    # Track.
    utils_lib.gl_expect_success('track file1')
    utils_lib.gl_expect_error('track file1')  # file1 is already tracked.
    utils_lib.gl_expect_error('track non-existent')
    # Untrack.
    utils_lib.gl_expect_success('untrack file1')
    utils_lib.gl_expect_success('untrack file1')  # file1 is already untracked.
    utils_lib.gl_expect_error('untrack non-existent')
    # Commit.
    utils_lib.gl_expect_success('commit -m"file1 commit"')
    utils_lib.gl_expect_error('commit -m"nothing to commit"')
    # History.
    if 'file1 commit' not in utils_lib.gl_expect_success('history')[0]:
      self.fail('Commit didn\'t appear in history')
    # Branch.
    # Make some changes in file1 and branch out.
    utils_lib.write_file('file1', 'New contents of file1')
    utils_lib.gl_expect_success('branch branch1')
    if 'New' in utils_lib.read_file('file1'):
      self.fail('Branch not independent!')
    # Switch back to master branch, check that contents are the same as before.
    utils_lib.gl_expect_success('branch master')
    if 'New' not in utils_lib.read_file('file1'):
      self.fail('Branch not independent!')
    out, _ = utils_lib.gl_expect_success('branch')
    if '* master' not in out:
      self.fail('Branch status output wrong')
    if 'branch1' not in out:
      self.fail('Branch status output wrong')

    utils_lib.gl_expect_success('branch branch1')
    utils_lib.gl_expect_success('branch branch2')
    utils_lib.gl_expect_success('branch branch-conflict1')
    utils_lib.gl_expect_success('branch branch-conflict2')
    utils_lib.gl_expect_success('branch master')
    utils_lib.gl_expect_success('commit -m"New contents commit"')

    # Rebase.
    utils_lib.gl_expect_success('branch branch1')
    utils_lib.gl_expect_error('rebase')  # no upstream set.
    utils_lib.gl_expect_success('rebase master')
    if 'file1 commit' not in utils_lib.gl_expect_success('history')[0]:
      self.fail()

    # Merge.
    utils_lib.gl_expect_success('branch branch2')
    utils_lib.gl_expect_error('merge')  # no upstream set.
    utils_lib.gl_expect_success('merge master')
    if 'file1 commit' not in utils_lib.gl_expect_success('history')[0]:
      self.fail()

    # Conflicting rebase.
    utils_lib.gl_expect_success('branch branch-conflict1')
    utils_lib.write_file('file1', 'Conflicting changes to file1')
    utils_lib.gl_expect_success('commit -m"changes in branch-conflict1"')
    if 'conflict' not in utils_lib.gl_expect_error('rebase master')[1]:
      self.fail()
    if 'file1 (with conflicts)' not in utils_lib.gl_expect_success('status')[0]:
      self.fail()

    # Try aborting.
    utils_lib.gl_expect_success('rebase --abort')
    if 'file1' in utils_lib.gl_expect_success('status')[0]:
      self.fail()

    # Ok, now let's fix the conflicts.
    if 'conflict' not in utils_lib.gl_expect_error('rebase master')[1]:
      self.fail()
    if 'file1 (with conflicts)' not in utils_lib.gl_expect_success('status')[0]:
      self.fail()

    utils_lib.write_file('file1', 'Fixed conflicts!')
    utils_lib.gl_expect_error('commit -m"shouldn\'t work (resolve not called)"')
    utils_lib.gl_expect_error('resolve nonexistentfile')
    utils_lib.gl_expect_success('resolve file1')
    utils_lib.gl_expect_success('commit -m"fixed conflicts"')


class TestCommit(TestEndToEnd):

  TRACKED_FP = 'file1'
  UNTRACKED_FP = 'file2'
  FPS = [TRACKED_FP, UNTRACKED_FP]

  def setUp(self):
    super(TestCommit, self).setUp()
    utils_lib.write_file(self.TRACKED_FP)
    utils_lib.write_file(self.UNTRACKED_FP)
    utils_lib.gl_expect_success('track {0}'.format(self.TRACKED_FP))

  # Happy paths.
  def test_commit(self):
    utils_lib.gl_expect_success('commit -m"msg"')
    self.__assert_commit(self.TRACKED_FP)

  def test_commit_only(self):
    utils_lib.gl_expect_success('commit -m"msg" {0}'.format(self.TRACKED_FP))
    self.__assert_commit(self.TRACKED_FP)

  def test_commit_only_untrack(self):
    utils_lib.gl_expect_success('commit -m"msg" {0}'.format(self.UNTRACKED_FP))
    self.__assert_commit(self.UNTRACKED_FP)

  def test_commit_inc(self):
    utils_lib.gl_expect_success(
        'commit -m"msg" -inc {0}'.format(self.UNTRACKED_FP))
    self.__assert_commit(self.TRACKED_FP, self.UNTRACKED_FP)

  def test_commit_exc_inc(self):
    utils_lib.gl_expect_success(
        'commit -m"msg" -inc {0} -exc {1}'.format(
            self.UNTRACKED_FP, self.TRACKED_FP))
    self.__assert_commit(self.UNTRACKED_FP)

  # Error paths.
  def test_commit_no_files(self):
    utils_lib.gl_expect_error('commit -m"msg" -exc {0}'.format(self.TRACKED_FP))
    utils_lib.gl_expect_error('commit -m"msg" nonexistentfp')
    utils_lib.gl_expect_error('commit -m"msg" -exc nonexistentfp')
    utils_lib.gl_expect_error('commit -m"msg" -inc nonexistentfp')

  def test_commit_dir(self):
    utils_lib.write_file('dir/f')
    utils_lib.gl_expect_error('commit -m"msg" dir')

  def __assert_commit(self, *expected_committed):
    st = utils_lib.gl_expect_success('status')[0]
    h = utils_lib.gl_expect_success('history -v')[0]
    for fp in expected_committed:
      if fp in st or fp not in h:
        self.fail('{0} was apparently not committed!'.format(fp))
    expected_not_committed = [
        fp for fp in self.FPS if fp not in expected_committed]
    for fp in expected_not_committed:
      if fp not in st or fp in h:
        self.fail('{0} was apparently committed!'.format(fp))


class TestBranch(TestEndToEnd):

  BRANCH_1 = 'branch1'
  BRANCH_2 = 'branch2'

  def setUp(self):
    super(TestBranch, self).setUp()
    utils_lib.write_file('f')
    utils_lib.gl_expect_success('commit f -msg"commit"')

  def test_create(self):
    utils_lib.gl_expect_success('branch {0}'.format(self.BRANCH_1))
    utils_lib.gl_expect_error('branch {0}'.format(self.BRANCH_1))
    utils_lib.gl_expect_error('branch evil_named_branch')
    if self.BRANCH_1 not in utils_lib.gl_expect_success('branch')[0]:
      self.fail()

  def test_remove(self):
    utils_lib.gl_expect_success('branch {0}'.format(self.BRANCH_1))
    utils_lib.gl_expect_error('branch -d {0}'.format(self.BRANCH_1))
    utils_lib.gl_expect_success('branch {0}'.format(self.BRANCH_2))
    utils_lib.gl_expect_success(
        'branch -d {0}'.format(self.BRANCH_1), pre_cmd='echo "n"')
    utils_lib.gl_expect_success(
        'branch -d {0}'.format(self.BRANCH_1), pre_cmd='echo "y"')
    if self.BRANCH_1 in utils_lib.gl_expect_success('branch')[0]:
      self.fail()


class TestDiff(TestEndToEnd):

  TRACKED_FP = 't_fp'
  UNTRACKED_FP = 'u_fp'

  def setUp(self):
    super(TestDiff, self).setUp()
    utils_lib.write_file(self.TRACKED_FP)
    utils_lib.gl_expect_success(
        'commit {0} -msg"commit"'.format(self.TRACKED_FP))
    utils_lib.write_file(self.UNTRACKED_FP)

  def test_empty_diff(self):
    if 'Nothing to diff' not in utils_lib.gl_expect_success('diff')[0]:
      self.fail()

  def test_diff_nonexistent_fp(self):
    _, err = utils_lib.gl_expect_error('diff {0}'.format('file'))
    if 'non-existent' not in err:
      self.fail()

  def test_basic_diff(self):
    utils_lib.write_file(self.TRACKED_FP, contents='contents')
    out1 = utils_lib.gl_expect_success('diff')[0]
    if '+contents' not in out1:
      self.fail()
    out2 = utils_lib.gl_expect_success('diff {0}'.format(self.TRACKED_FP))[0]
    if '+contents' not in out2:
      self.fail()
    self.assertEqual(out1, out2)


# TODO(sperezde): add more performance tests to check that we're not dropping
# the ball: We should try to keep Gitless's performance reasonably close to
# Git's.
class TestPerformance(TestEndToEnd):

  FPS_QTY = 10000

  def setUp(self):
    super(TestPerformance, self).setUp()
    for i in range(0, self.FPS_QTY):
      fp = 'f' + str(i)
      utils_lib.write_file(fp, fp)

  def test_status_performance(self):
    """Assert that gl status is not too slow."""

    def assert_status_performance():
      # The test fails if gl status takes more than 100 times
      # the time git status took.
      MAX_TOLERANCE = 100

      t = time.time()
      utils_lib.gl_call('status')
      gl_t = time.time() - t

      t = time.time()
      utils_lib.git_call('status')
      git_t = time.time() - t

      self.assertTrue(
          gl_t < git_t*MAX_TOLERANCE,
          msg='gl_t {0}, git_t {1}'.format(gl_t, git_t))

    # All files are untracked.
    assert_status_performance()
    # Track all files, repeat.
    logging.info('Doing a massive git add, this might take a while')
    utils_lib.git_call('add .')
    logging.info('Done')
    assert_status_performance()

  def test_branch_switch_performance(self):
    """Assert that switching branches is not too slow."""
    MAX_TOLERANCE = 100

    # Temporary hack until we get stuff working smoothly when the repo has no
    # commits.
    utils_lib.gl_call('commit -m"commit" f1')

    t = time.time()
    utils_lib.gl_call('branch develop')
    gl_t = time.time() - t

    # go back to previous state.
    utils_lib.gl_call('branch master')

    # do the same for git.
    t = time.time()
    utils_lib.git_call('branch gitdev')
    utils_lib.git_call('stash save --all')
    utils_lib.git_call('checkout gitdev')
    git_t = time.time() - t

    self.assertTrue(
        gl_t < git_t*MAX_TOLERANCE,
        msg='gl_t {0}, git_t {1}'.format(gl_t, git_t))


if __name__ == '__main__':
  unittest.main()
