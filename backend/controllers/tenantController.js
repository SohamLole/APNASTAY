const Tenant = require('../models/Tenant');
const Bed = require('../models/Bed');
const Payment = require('../models/Payment');

// @desc    Get all tenants
// @route   GET /api/tenants
// @access  Private/Admin
exports.getTenants = async (req, res, next) => {
  try {
    const tenants = await Tenant.find().populate({
      path: 'bedId',
      populate: {
        path: 'roomId',
        populate: {
          path: 'buildingId'
        }
      }
    });

    res.status(200).json({
      success: true,
      count: tenants.length,
      data: tenants
    });
  } catch (err) {
    next(err);
  }
};

// @desc    Get single tenant
// @route   GET /api/tenants/:id
// @access  Private
exports.getTenant = async (req, res, next) => {
  try {
    const tenant = await Tenant.findById(req.params.id).populate({
      path: 'bedId',
      populate: {
        path: 'roomId',
        populate: {
          path: 'buildingId'
        }
      }
    });

    if (!tenant) {
      return res.status(404).json({
        success: false,
        message: 'Tenant not found'
      });
    }

    // Ensure tenant or admin is accessing
    if (req.user.role !== 'admin' && tenant._id.toString() !== req.user.id) {
      return res.status(401).json({
        success: false,
        message: 'Not authorized to access this tenant'
      });
    }

    res.status(200).json({
      success: true,
      data: tenant
    });
  } catch (err) {
    next(err);
  }
};

// @desc    Create tenant
// @route   POST /api/tenants
// @access  Private/Admin
exports.createTenant = async (req, res, next) => {
  try {
    const tenant = await Tenant.create(req.body);

    res.status(201).json({
      success: true,
      data: tenant
    });
  } catch (err) {
    next(err);
  }
};

// @desc    Update tenant
// @route   PUT /api/tenants/:id
// @access  Private
exports.updateTenant = async (req, res, next) => {
  try {
    let tenant = await Tenant.findById(req.params.id);

    if (!tenant) {
      return res.status(404).json({
        success: false,
        message: 'Tenant not found'
      });
    }

    // Ensure tenant or admin is updating
    if (req.user.role !== 'admin' && tenant._id.toString() !== req.user.id) {
      return res.status(401).json({
        success: false,
        message: 'Not authorized to update this tenant'
      });
    }

    // Update tenant
    tenant = await Tenant.findByIdAndUpdate(req.params.id, req.body, {
      new: true,
      runValidators: true
    });

    res.status(200).json({
      success: true,
      data: tenant
    });
  } catch (err) {
    next(err);
  }
};

// @desc    Delete tenant
// @route   DELETE /api/tenants/:id
// @access  Private/Admin
exports.deleteTenant = async (req, res, next) => {
  try {
    const tenant = await Tenant.findById(req.params.id);

    if (!tenant) {
      return res.status(404).json({
        success: false,
        message: 'Tenant not found'
      });
    }

    // Free up the bed if assigned
    if (tenant.bedId) {
      await Bed.findByIdAndUpdate(tenant.bedId, {
        status: 'vacant',
        tenantId: null
      });
    }

    await tenant.remove();

    res.status(200).json({
      success: true,
      data: {}
    });
  } catch (err) {
    next(err);
  }
};

// @desc    Get tenant payments
// @route   GET /api/tenants/:id/payments
// @access  Private
exports.getTenantPayments = async (req, res, next) => {
  try {
    const tenant = await Tenant.findById(req.params.id);

    if (!tenant) {
      return res.status(404).json({
        success: false,
        message: 'Tenant not found'
      });
    }

    // Ensure tenant or admin is accessing
    if (req.user.role !== 'admin' && tenant._id.toString() !== req.user.id) {
      return res.status(401).json({
        success: false,
        message: 'Not authorized to access this tenant'
      });
    }

    const payments = await Payment.find({ tenantId: req.params.id })
      .sort({ year: -1, month: -1 });

    res.status(200).json({
      success: true,
      count: payments.length,
      data: payments
    });
  } catch (err) {
    next(err);
  }
};