const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');
const Tenant = require('../models/Tenant');

// Admin credentials (in production, store in database with proper security)
const ADMIN_CREDENTIALS = {
  username: 'admin',
  password: process.env.ADMIN_PASSWORD || 'admin123'
};

// @desc    Authenticate tenant
// @route   POST /api/auth/tenant
// @access  Public
exports.authenticateTenant = async (req, res, next) => {
  const { username, password } = req.body;

  try {
    // Check for tenant
    const tenant = await Tenant.findOne({ username }).select('+password');
    
    if (!tenant) {
      return res.status(401).json({ success: false, message: 'Invalid credentials' });
    }

    // Check password
    const isMatch = await bcrypt.compare(password, tenant.password);
    
    if (!isMatch) {
      return res.status(401).json({ success: false, message: 'Invalid credentials' });
    }

    // Create token
    const token = jwt.sign({ id: tenant._id, role: 'tenant' }, process.env.JWT_SECRET, {
      expiresIn: process.env.JWT_EXPIRE
    });

    res.status(200).json({
      success: true,
      token,
      user: {
        id: tenant._id,
        username: tenant.username,
        fullName: tenant.fullName,
        role: 'tenant'
      }
    });
  } catch (err) {
    next(err);
  }
};

// @desc    Authenticate admin
// @route   POST /api/auth/admin
// @access  Public
exports.authenticateAdmin = async (req, res, next) => {
  const { username, password } = req.body;

  try {
    // Check admin credentials
    if (username !== ADMIN_CREDENTIALS.username || password !== ADMIN_CREDENTIALS.password) {
      return res.status(401).json({ success: false, message: 'Invalid credentials' });
    }

    // Create token
    const token = jwt.sign({ username, role: 'admin' }, process.env.JWT_SECRET, {
      expiresIn: process.env.JWT_EXPIRE
    });

    res.status(200).json({
      success: true,
      token,
      user: {
        username,
        role: 'admin'
      }
    });
  } catch (err) {
    next(err);
  }
};

// @desc    Get current logged in user
// @route   GET /api/auth/me
// @access  Private
exports.getMe = async (req, res, next) => {
  try {
    if (req.user.role === 'tenant') {
      const tenant = await Tenant.findById(req.user.id).select('-password');
      res.status(200).json({
        success: true,
        data: tenant,
        role: 'tenant'
      });
    } else {
      res.status(200).json({
        success: true,
        data: {
          username: req.user.username
        },
        role: 'admin'
      });
    }
  } catch (err) {
    next(err);
  }
};