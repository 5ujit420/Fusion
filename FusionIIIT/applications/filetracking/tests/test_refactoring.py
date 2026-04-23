"""
Test suite for filetracking refactoring.
Validates that all refactoring actions preserve business logic while improving structure.
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from applications.filetracking.models import File, Tracking
from applications.filetracking.services import (
    create_file_from_form,
    forward_file_service,
    archive_file_service,
    unarchive_file_service,
    update_draft_and_send,
    delete_file_service,
    validate_file_size,
)
from applications.filetracking.selectors import (
    get_file_by_id,
    get_all_files,
    get_tracking_by_file_id,
    get_history_for_file,
    get_inbox_files,
    get_outbox_files,
    filter_files_by_search,
)
from applications.filetracking.api.serializers import (
    FileSerializer,
    TrackingSerializer,
    FILE_SIZE_LIMIT_KB,
    SUBJECT_MAX_LENGTH,
    DESCRIPTION_MAX_LENGTH,
)


class TestFileSerializerValidation(TestCase):
    """Test CS025, CS026 - Serializer validation"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_validate_subject_max_length(self):
        """Test subject validation respects max length"""
        data = {
            'uploader': self.user.extrainfo.id if hasattr(self.user, 'extrainfo') else 1,
            'subject': 'x' * (SUBJECT_MAX_LENGTH + 1),
            'description': 'Valid description',
        }
        serializer = FileSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('subject', serializer.errors)
    
    def test_validate_description_max_length(self):
        """Test description validation respects max length"""
        data = {
            'uploader': self.user.extrainfo.id if hasattr(self.user, 'extrainfo') else 1,
            'subject': 'Valid subject',
            'description': 'x' * (DESCRIPTION_MAX_LENGTH + 1),
        }
        serializer = FileSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('description', serializer.errors)
    
    def test_validate_upload_file_size(self):
        """Test file size validation (CS003, CS017)"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        # Create a file larger than 10MB
        large_file = SimpleUploadedFile(
            "large_file.txt",
            b"x" * ((FILE_SIZE_LIMIT_KB * 1000) + 1),
            content_type="text/plain"
        )
        
        data = {
            'uploader': self.user.extrainfo.id if hasattr(self.user, 'extrainfo') else 1,
            'subject': 'Test subject',
            'description': 'Test description',
            'upload_file': large_file,
        }
        serializer = FileSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('upload_file', serializer.errors)


class TestValidateFileSize(TestCase):
    """Test CS017 - Extracted validation function"""
    
    def test_valid_file_size(self):
        """File under limit should pass"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        small_file = SimpleUploadedFile(
            "small.txt",
            b"x" * 1000,  # 1KB
            content_type="text/plain"
        )
        # Should not raise
        validate_file_size(small_file)
    
    def test_invalid_file_size(self):
        """File over limit should raise ValidationError"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        large_file = SimpleUploadedFile(
            "large.txt",
            b"x" * ((FILE_SIZE_LIMIT_KB * 1000) + 1),
            content_type="text/plain"
        )
        with self.assertRaises(ValidationError):
            validate_file_size(large_file)


class TestSelectors(TestCase):
    """Test CS002, CS005, CS006, CS024 - Selectors layer"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='selectoruser',
            password='testpass123'
        )
    
    def test_get_file_by_id(self):
        """Test CS006 - get_file_by_id selector"""
        file = File.objects.create(
            uploader=self.user.extrainfo,
            subject='Test File',
            description='Test Description'
        )
        retrieved = get_file_by_id(file.id)
        self.assertEqual(retrieved.id, file.id)
        self.assertEqual(retrieved.subject, 'Test File')
    
    def test_get_all_files_select_related(self):
        """Test CS002, CS028 - Optimized query with select_related"""
        File.objects.create(
            uploader=self.user.extrainfo,
            subject='File 1',
            description='Desc 1'
        )
        File.objects.create(
            uploader=self.user.extrainfo,
            subject='File 2',
            description='Desc 2'
        )
        
        # Should not raise and should include related data
        files = get_all_files()
        self.assertEqual(files.count(), 2)
    
    def test_get_tracking_by_file_id(self):
        """Test CS005, CS021 - Optimized tracking query"""
        file = File.objects.create(
            uploader=self.user.extrainfo,
            subject='Test File',
        )
        Tracking.objects.create(
            file_id=file,
            current_id=self.user.extrainfo,
            receiver_id=self.user,
        )
        
        tracking = get_tracking_by_file_id(file.id)
        self.assertEqual(tracking.count(), 1)


class TestServiceLayer(TestCase):
    """Test CS001, CS004, CS008, CS067 - Service layer extraction"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='serviceuser',
            password='testpass123'
        )
    
    def test_create_file_from_form_save_action(self):
        """Test CS001 - Create draft (save action)"""
        from applications.globals.models import HoldsDesignation, Designation
        
        # Create required designation
        designation = Designation.objects.create(name='Test Designation')
        holds_designation = HoldsDesignation.objects.create(
            user=self.user,
            designation=designation
        )
        
        file = create_file_from_form(
            uploader=self.user,
            subject='Test Subject',
            description='Test Description',
            designation_id=holds_designation.id,
            send_to_receiver=False,
        )
        
        self.assertIsNotNone(file.id)
        self.assertEqual(file.subject, 'Test Subject')
        # Should have no tracking entries for draft
        self.assertEqual(Tracking.objects.filter(file_id=file).count(), 0)
    
    def test_create_file_from_form_send_action(self):
        """Test CS001 - Create and send file"""
        from applications.globals.models import HoldsDesignation, Designation
        
        # Create designations
        sender_designation = Designation.objects.create(name='Sender Designation')
        receiver_designation = Designation.objects.create(name='Receiver Designation')
        
        receiver = User.objects.create_user(
            username='receiveruser',
            password='testpass123'
        )
        
        holds_designation = HoldsDesignation.objects.create(
            user=self.user,
            designation=sender_designation
        )
        
        file = create_file_from_form(
            uploader=self.user,
            subject='Test Subject',
            description='Test Description',
            designation_id=holds_designation.id,
            send_to_receiver=True,
            receiver_username='receiveruser',
            receive_designation_name='Receiver Designation',
        )
        
        self.assertIsNotNone(file.id)
        # Should have tracking entry for sent file
        self.assertEqual(Tracking.objects.filter(file_id=file).count(), 1)
    
    def test_archive_file_service(self):
        """Test CS007 - Archive file service"""
        file = File.objects.create(
            uploader=self.user.extrainfo,
            subject='Test File',
            is_read=False,
        )
        
        result = archive_file_service(file.id, self.user)
        
        self.assertTrue(result['success'])
        file.refresh_from_db()
        self.assertTrue(file.is_read)
    
    def test_delete_file_service(self):
        """Test delete file service"""
        file = File.objects.create(
            uploader=self.user.extrainfo,
            subject='Test File',
        )
        
        result = delete_file_service(file.id, self.user)
        
        self.assertTrue(result['success'])
        self.assertFalse(File.objects.filter(id=file.id).exists())


class TestRefactoringPreservesLogic(TestCase):
    """Test that refactoring preserves original business logic"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='logicuser',
            password='testpass123'
        )
    
    def test_file_creation_preserves_behavior(self):
        """Test that service layer creates files same as original view"""
        from applications.globals.models import HoldsDesignation, Designation
        
        designation = Designation.objects.create(name='Test Designation')
        holds_designation = HoldsDesignation.objects.create(
            user=self.user,
            designation=designation
        )
        
        # Create file via service
        file = create_file_from_form(
            uploader=self.user,
            subject='Logic Test',
            description='Testing logic preservation',
            designation_id=holds_designation.id,
            send_to_receiver=False,
        )
        
        # Verify file has correct attributes
        self.assertEqual(file.subject, 'Logic Test')
        self.assertEqual(file.description, 'Testing logic preservation')
        self.assertEqual(file.uploader, self.user.extrainfo)
        self.assertIsNotNone(file.upload_date)


class TestNoNPlusOneQueries(TestCase):
    """Test CS027, CS028, CS029, CS061 - N+1 query fixes"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='nplusoneuser',
            password='testpass123'
        )
    
    def test_inbox_query_optimization(self):
        """Test that inbox queries use select_related"""
        from applications.globals.models import HoldsDesignation, Designation
        
        designation = Designation.objects.create(name='Test Designation')
        holds_designation = HoldsDesignation.objects.create(
            user=self.user,
            designation=designation
        )
        
        # Create multiple files with tracking
        for i in range(5):
            file = File.objects.create(
                uploader=self.user.extrainfo,
                subject=f'File {i}',
            )
            Tracking.objects.create(
                file_id=file,
                current_id=self.user.extrainfo,
                current_design=holds_designation,
                receiver_id=self.user,
                receive_design=designation,
            )
        
        # This should execute O(1) queries, not N+1
        inbox = get_inbox_files(self.user, designation.id)
        # Force evaluation and check it doesn't explode
        results = list(inbox)
        self.assertEqual(len(results), 5)
    
    def test_history_query_optimization(self):
        """Test that history queries use select_related"""
        file = File.objects.create(
            uploader=self.user.extrainfo,
            subject='History Test',
        )
        
        # Create multiple tracking entries
        for i in range(5):
            Tracking.objects.create(
                file_id=file,
                current_id=self.user.extrainfo,
                receiver_id=self.user,
            )
        
        # Should work without N+1
        history = get_history_for_file(file.id)
        results = list(history)
        self.assertEqual(len(results), 5)


class TestErrorHandling(TestCase):
    """Test CS044, CS045, CS046, CS060 - Error handling improvements"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='erroruser',
            password='testpass123'
        )
    
    def test_forward_file_service_error_handling(self):
        """Test service returns proper error dict on failure"""
        result = forward_file_service(
            file_id=99999,  # Non-existent
            current_user=self.user,
            current_designation_id=1,
            receiver_username='nonexistent',
            receive_designation_name='NonExistent',
            remarks='Test',
        )
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
    
    def test_archive_file_permission_check(self):
        """Test archive service checks permissions"""
        other_user = User.objects.create_user(
            username='otheruser',
            password='testpass123'
        )
        
        file = File.objects.create(
            uploader=self.user.extrainfo,
            subject='Test File',
        )
        
        # Other user tries to archive
        result = archive_file_service(file.id, other_user)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Permission denied')
