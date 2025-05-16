const express = require('express');
const {
  authenticateTenant,
  authenticateAdmin,
  getMe
} = require('../controllers/authController');

const router = express.Router();

const { protect } = require('../middleware/auth');

router.post('/tenant', authenticateTenant);
router.post('/admin', authenticateAdmin);
router.get('/me', protect, getMe);

module.exports = router;