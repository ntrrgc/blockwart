# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from os import makedirs
from shutil import rmtree
from tempfile import mkstemp
from unittest import TestCase

from mako.exceptions import CompileException
from mock import call, MagicMock, patch

from blockwart.exceptions import BundleError
from blockwart.items import files, ItemStatus
from blockwart.utils.text import green, red


class ContentProcessorMakoTest(TestCase):
    """
    Tests blockwart.items.files.content_processor_mako.
    """
    def test_template(self):
        item = MagicMock()
        item.node.name = "localhost"
        item.attributes = {
            'context': {
                'number': "47",
            },
            'encoding': "utf-8",
        }
        item._template_content = "Hi from ${number}@${node.name}!"
        self.assertEqual(
            files.content_processor_mako(item),
            "Hi from 47@localhost!",
        )


class ContentProcessorTextTest(TestCase):
    """
    Tests blockwart.items.files.content_processor_text.
    """
    def test_template(self):
        bundle = MagicMock()
        bundle.node.name = "localhost"
        item = files.File(
            bundle,
            "/foo",
            {
                'content': "Hi from ${node.name}!",
                'encoding': "utf-8",
            },
        )
        self.assertEqual(
            files.content_processor_text(item),
            "Hi from ${node.name}!",
        )

    def test_encoding(self):
        bundle = MagicMock()
        bundle.node.name = "localhost"
        item = files.File(
            bundle,
            "/foo",
            {
                'content': "Hellö!".encode("utf-8"),
                'encoding': "latin-1",
            },
        )
        self.assertEqual(
            files.content_processor_text(item).decode("latin-1"),
            "Hellö!",
        )


class DiffTest(TestCase):
    """
    Tests blockwart.items.files.diff.
    """
    def test_diff(self):
        content_old = (
            "line1\n"
            "line2\n"
        )
        content_new = (
            "line1\n"
            "line3\n"
        )
        self.assertEqual(
            files.diff(content_old, content_new, "/foo"),
            (
                red("--- /foo") + "\n" +
                green("+++ <blockwart content>") + "\n" +
                "@@ -1,2 +1,2 @@\n"
                " line1\n" +
                red("-line2") + "\n" +
                green("+line3") + "\n"
            ),
        )

    def test_encoding(self):
        content_old = (
            "lineö1\n".encode("utf-8")
        )
        content_new = (
            "lineö1\n".encode("latin-1")
        )
        self.assertEqual(
            files.diff(content_old, content_new, "/foo", encoding_hint="latin-1"),
            (
                red("--- /foo") + "\n" +
                green("+++ <blockwart content>") + "\n" +
                "@@ -1 +1 @@\n" +
                red("-lineö1") + "\n" +
                green("+lineö1") + " (line encoded in latin-1)\n"
            ),
        )

    def test_encoding_unknown(self):
        content_old = (
            "lineö1\n".encode("utf-8")
        )
        content_new = (
            "lineö1\n".encode("latin-1")
        )
        self.assertEqual(
            files.diff(content_old, content_new, "/foo", encoding_hint="ascii"),
            (
                red("--- /foo") + "\n" +
                green("+++ <blockwart content>") + "\n" +
                "@@ -1 +1 @@\n" +
                red("-lineö1") + "\n" +
                green("+") + " (line not encoded in UTF-8 or ascii)\n"
            ),
        )

    def test_long_line(self):
        content_old = (
            "line1\n"
        )
        content_new = (
            "line1" + 500 * "1" + "\n"
        )
        self.assertEqual(
            files.diff(content_old, content_new, "/foo"),
            (
                red("--- /foo") + "\n" +
                green("+++ <blockwart content>") + "\n" +
                "@@ -1 +1 @@\n" +
                red("-line1") + "\n" +
                green("+line111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111") +
                " (line truncated after 128 characters)\n"
            ),
        )


class FileContentHashTest(TestCase):
    """
    Tests blockwart.items.files.File.content_hash.
    """
    @patch('blockwart.items.files.hash_local_file', return_value="47")
    def test_binary(self, hash_local_file):
        bundle = MagicMock()
        bundle.bundle_dir = "/b/dir"
        f = files.File(
            bundle,
            "/foo",
            {'content_type': 'binary', 'source': 'foobar'},
        )
        self.assertEqual(f.content_hash, "47")
        hash_local_file.assert_called_once_with("/b/dir/files/foobar")


class FileFixTest(TestCase):
    """
    Tests blockwart.items.files.File.fix.
    """
    @patch('blockwart.items.files.File._fix_content')
    @patch('blockwart.items.files.File._fix_mode')
    @patch('blockwart.items.files.File._fix_owner')
    @patch('blockwart.items.files.File._fix_type')
    def test_type(self, fix_type, fix_owner, fix_mode, fix_content):
        f = files.File(MagicMock(), "/foo", {})
        pinfo = MagicMock()
        pinfo.exists = False
        status = ItemStatus(correct=False, info={
            'path_info': pinfo,
            'needs_fixing': ['type', 'content', 'mode', 'owner'],
        })
        f.fix(status)
        fix_type.assert_called_once_with(status)
        fix_content.assert_called_once_with(status)

    @patch('blockwart.items.files.File._fix_content')
    @patch('blockwart.items.files.File._fix_mode')
    @patch('blockwart.items.files.File._fix_owner')
    @patch('blockwart.items.files.File._fix_type')
    def test_content(self, fix_type, fix_owner, fix_mode, fix_content):
        f = files.File(MagicMock(), "/foo", {})
        pinfo = MagicMock()
        pinfo.exists = False
        status = ItemStatus(correct=False, info={
            'path_info': pinfo,
            'needs_fixing': ['content'],
        })
        f.fix(status)
        self.assertFalse(fix_type.called)
        fix_content.assert_called_once_with(status)
        self.assertFalse(fix_mode.called)
        self.assertFalse(fix_owner.called)

    @patch('blockwart.items.files.File._fix_content')
    @patch('blockwart.items.files.File._fix_mode')
    @patch('blockwart.items.files.File._fix_owner')
    @patch('blockwart.items.files.File._fix_type')
    def test_mode(self, fix_type, fix_owner, fix_mode, fix_content):
        f = files.File(MagicMock(), "/foo", {})
        pinfo = MagicMock()
        pinfo.exists = False
        status = ItemStatus(correct=False, info={
            'path_info': pinfo,
            'needs_fixing': ['mode'],
        })
        f.fix(status)
        self.assertFalse(fix_type.called)
        fix_mode.assert_called_once_with(status)
        self.assertFalse(fix_content.called)
        self.assertFalse(fix_owner.called)

    @patch('blockwart.items.files.File._fix_content')
    @patch('blockwart.items.files.File._fix_mode')
    @patch('blockwart.items.files.File._fix_owner')
    @patch('blockwart.items.files.File._fix_type')
    def test_owner(self, fix_type, fix_owner, fix_mode, fix_content):
        f = files.File(MagicMock(), "/foo", {})
        pinfo = MagicMock()
        pinfo.exists = False
        status = ItemStatus(correct=False, info={
            'path_info': pinfo,
            'needs_fixing': ['owner'],
        })
        f.fix(status)
        self.assertFalse(fix_type.called)
        fix_owner.assert_called_once_with(status)
        self.assertFalse(fix_content.called)
        self.assertFalse(fix_mode.called)

    @patch('blockwart.items.files.File._fix_content')
    @patch('blockwart.items.files.File._fix_mode')
    @patch('blockwart.items.files.File._fix_owner')
    @patch('blockwart.items.files.File._fix_type')
    def test_combined(self, fix_type, fix_owner, fix_mode, fix_content):
        f = files.File(MagicMock(), "/foo", {})
        pinfo = MagicMock()
        pinfo.exists = False
        status = ItemStatus(correct=False, info={
            'path_info': pinfo,
            'needs_fixing': ['owner', 'mode'],
        })
        f.fix(status)
        self.assertFalse(fix_type.called)
        fix_owner.assert_called_once_with(status)
        fix_mode.assert_called_once_with(status)
        self.assertFalse(fix_content.called)


class FileFixContentTest(TestCase):
    """
    Tests blockwart.items.files.File._fix_content.
    """
    def test_binary(self):
        node = MagicMock()
        bundle = MagicMock()
        bundle.bundle_dir = "/b/dir"
        bundle.node = node
        f = files.File(
            bundle,
            "/foo",
            {'content_type': 'binary', 'source': 'foobar'},
        )
        f._fix_content(MagicMock())
        node.upload.assert_called_once_with(
            "/b/dir/files/foobar",
            "/foo",
            owner="root",
            group="root",
            mode="0664",
        )

    def test_regular(self):
        node = MagicMock()
        bundle = MagicMock()
        bundle.bundle_dir = "/b/dir"
        bundle.node = node
        f = files.File(
            bundle,
            "/foo",
            {'content': "47", 'content_type': 'mako'},
        )
        f._fix_content(MagicMock())
        node.upload.assert_called_once()


class FileFixModeTest(TestCase):
    """
    Tests blockwart.items.files.File._fix_mode.
    """
    def test_chmod(self):
        node = MagicMock()
        bundle = MagicMock()
        bundle.node = node
        f = files.File(
            bundle,
            "/foo",
            {'mode': "1234"},
        )
        f._fix_mode(MagicMock())
        node.run.assert_called_once_with("chmod 1234 -- /foo")


class FileFixOwnerTest(TestCase):
    """
    Tests blockwart.items.files.File._fix_owner.
    """
    def test_chmod(self):
        node = MagicMock()
        bundle = MagicMock()
        bundle.node = node
        f = files.File(
            bundle,
            "/foo",
            {'owner': "jcleese", 'group': "mp"},
        )
        f._fix_owner(MagicMock())
        node.run.assert_called_once_with("chown jcleese:mp -- /foo")


class FileFixTypeTest(TestCase):
    """
    Tests blockwart.items.files.File._fix_type.
    """
    @patch('blockwart.items.files.File._fix_content')
    def test_rm(self, fix_content):
        node = MagicMock()
        bundle = MagicMock()
        bundle.node = node
        f = files.File(
            bundle,
            "/foo",
            {},
        )
        f._fix_type(MagicMock())
        assert call("rm -rf -- /foo") in node.run.call_args_list
        assert call("mkdir -p -- /") in node.run.call_args_list
        fix_content.assert_called_once()


class FileGetAutoDepsTest(TestCase):
    """
    Tests blockwart.items.files.File.get_auto_deps.
    """
    def test_subdir(self):
        item1 = MagicMock()
        item1.ITEM_TYPE_NAME = "directory"
        item1.id = "directory:/foo/bar"
        item1.name = "/foo/bar"
        item2 = MagicMock()
        item2.ITEM_TYPE_NAME = "directory"
        item2.id = "directory:/bar/foo"
        item2.name = "/bar/foo"
        item3 = MagicMock()
        item3.ITEM_TYPE_NAME = "file"
        item3.id = "file:/foo/baz"
        item3.name = "/foo/baz"

        f = files.File(MagicMock(), "/foo/bar/baz", {})

        items = [item1, item2, item3, f]

        self.assertEqual(f.get_auto_deps(items), ["directory:/foo/bar"])

    def test_symdir(self):
        item1 = MagicMock()
        item1.ITEM_TYPE_NAME = "symlink"
        item1.id = "symlink:/foo/bar"
        item1.name = "/foo/bar"
        item2 = MagicMock()
        item2.ITEM_TYPE_NAME = "directory"
        item2.id = "directory:/bar/foo"
        item2.name = "/bar/foo"
        item3 = MagicMock()
        item3.ITEM_TYPE_NAME = "file"
        item3.id = "file:/foo/baz"
        item3.name = "/foo/baz"

        f = files.File(MagicMock(), "/foo/bar/baz", {})

        items = [item1, item2, item3, f]

        self.assertEqual(f.get_auto_deps(items), ["symlink:/foo/bar"])


class FileGetStatusTest(TestCase):
    """
    Tests blockwart.items.files.File.get_status.
    """
    @patch('blockwart.items.files.File.content_hash', new="47")
    @patch('blockwart.items.files.PathInfo')
    def test_mode(self, PathInfo):
        path_info = MagicMock()
        path_info.mode = "0777"
        path_info.owner = "root"
        path_info.group = "root"
        path_info.sha1 = "47"
        path_info.is_file = True
        PathInfo.return_value = path_info

        f = files.File(MagicMock(), "/foo", {
            'mode': "0664",
            'owner': "root",
            'group': "root",
        })
        status = f.get_status()
        self.assertFalse(status.correct)
        self.assertEqual(status.info['needs_fixing'], ['mode'])

    @patch('blockwart.items.files.File.content_hash', new="47")
    @patch('blockwart.items.files.PathInfo')
    def test_owner(self, PathInfo):
        path_info = MagicMock()
        path_info.mode = "0664"
        path_info.owner = "jdoe"
        path_info.group = "root"
        path_info.sha1 = "47"
        path_info.is_file = True
        PathInfo.return_value = path_info

        f = files.File(MagicMock(), "/foo", {
            'mode': "0664",
            'owner': "root",
            'group': "root",
        })
        status = f.get_status()
        self.assertFalse(status.correct)
        self.assertEqual(status.info['needs_fixing'], ['owner'])

    @patch('blockwart.items.files.File.content_hash', new="47")
    @patch('blockwart.items.files.PathInfo')
    def test_group(self, PathInfo):
        path_info = MagicMock()
        path_info.mode = "0664"
        path_info.owner = "root"
        path_info.group = "yolocrowd"
        path_info.sha1 = "47"
        path_info.is_file = True
        PathInfo.return_value = path_info

        f = files.File(MagicMock(), "/foo", {
            'mode': "0664",
            'owner': "root",
            'group': "root",
        })
        status = f.get_status()
        self.assertFalse(status.correct)
        self.assertEqual(status.info['needs_fixing'], ['group'])

    @patch('blockwart.items.files.File.content_hash', new="47")
    @patch('blockwart.items.files.PathInfo')
    def test_content(self, PathInfo):
        path_info = MagicMock()
        path_info.mode = "0664"
        path_info.owner = "root"
        path_info.group = "root"
        path_info.sha1 = "48"
        path_info.is_file = True
        PathInfo.return_value = path_info

        f = files.File(MagicMock(), "/foo", {
            'mode': "0664",
            'owner': "root",
            'group': "root",
        })
        status = f.get_status()
        self.assertFalse(status.correct)
        self.assertEqual(
            set(status.info['needs_fixing']),
            set(['content']),
        )

    @patch('blockwart.items.files.File.content_hash', new="47")
    @patch('blockwart.items.files.PathInfo')
    def test_type(self, PathInfo):
        path_info = MagicMock()
        path_info.mode = "0664"
        path_info.owner = "root"
        path_info.group = "root"
        path_info.sha1 = "47"
        path_info.is_file = False
        PathInfo.return_value = path_info

        f = files.File(MagicMock(), "/foo", {
            'mode': "0664",
            'owner': "root",
            'group': "root",
        })
        status = f.get_status()
        self.assertFalse(status.correct)
        self.assertEqual(
            set(status.info['needs_fixing']),
            set(['type']),
        )

    @patch('blockwart.items.files.File.content_hash', new="47")
    @patch('blockwart.items.files.PathInfo')
    def test_ok(self, PathInfo):
        path_info = MagicMock()
        path_info.mode = "0664"
        path_info.owner = "root"
        path_info.group = "root"
        path_info.sha1 = "47"
        path_info.is_file = True
        PathInfo.return_value = path_info

        f = files.File(MagicMock(), "/foo", {
            'mode': "0664",
            'owner': "root",
            'group': "root",
        })
        status = f.get_status()
        self.assertTrue(status.correct)
        self.assertEqual(status.info['needs_fixing'], [])


class FileTestTest(TestCase):
    """
    Tests blockwart.items.files.File.test.
    """
    def setUp(self):
        makedirs("/tmp/bw_file_test/files")
        with open("/tmp/bw_file_test/files/fail", 'w') as template:
            template.write("%goto fail")
        with open("/tmp/bw_file_test/files/success", 'w') as template:
            template.write("Hi!")

    def tearDown(self):
        rmtree("/tmp/bw_file_test")

    def test_missing_template(self):
        bundle = MagicMock()
        bundle.bundle_dir = "/bogus"
        f = files.File(bundle, "foo", { 'source': "bogus" })
        with self.assertRaises(BundleError):
            f.test()

    def test_content_fails(self):
        bundle = MagicMock()
        bundle.bundle_dir = "/tmp/bw_file_test"
        f = files.File(bundle, "foo", { 'content_type': 'mako', 'source': "fail" })
        with self.assertRaises(CompileException):
            f.test()

    def test_content_ok(self):
        bundle = MagicMock()
        bundle.bundle_dir = "/tmp/bw_file_test"
        f = files.File(bundle, "foo", { 'content_type': 'mako', 'source': "success" })
        f.test()


class HashLocalTest(TestCase):
    """
    Tests blockwart.items.files.hash_local_file.
    """
    def test_known_hash(self):
        _, filename = mkstemp()
        with open(filename, 'w') as f:
            f.write("47")
        self.assertEqual(
            files.hash_local_file(filename),
            "827bfc458708f0b442009c9c9836f7e4b65557fb",
        )


class ValidateAttributesTest(TestCase):
    """
    Tests blockwart.items.files.File.validate_attributes.
    """
    def test_validator_call(self):
        validator = MagicMock()
        attr_val = {
            'attr1': validator,
            'attr2': validator,
        }
        with patch('blockwart.items.files.ATTRIBUTE_VALIDATORS', new=attr_val):
            files.File.validate_attributes(
                MagicMock(),
                "item:id",
                {
                    'attr1': 1,
                    'attr2': 2,
                },
            )
        validator.assert_any_call("item:id", 1)
        validator.assert_any_call("item:id", 2)
        self.assertEqual(validator.call_count, 2)
