const Bed = require('../models/Bed');
const Tenant = require('../models/Tenant');
const Room = require('../models/Room');

// @desc    Get all beds
// @route   GET /api/beds
// @access  Private/Admin
exports.getBeds = async (req, res, next) => {
  try {
    let query;
    
    // Copy req.query
    const reqQuery = { ...req.query };
    
    // Fields to exclude
    const removeFields = ['select', 'sort', 'page', 'limit'];
    
    // Loop over removeFields and delete them from reqQuery
    removeFields.forEach(param => delete reqQuery[param]);
    
    // Create query string
    let queryStr = JSON.stringify(reqQuery);
    
    // Create operators ($gt, $gte, etc)
    queryStr = queryStr.replace(/\b(gt|gte|lt|lte|in)\b/g, match => `$${match}`);
    
    // Finding resource
    query = Bed.find(JSON.parse(queryStr)).populate('roomId tenantId');
    
    // Select Fields
    if (req.query.select) {
      const fields = req.query.select.split(',').join(' ');
      query = query.select(fields);
    }
    
    // Sort
    if (req.query.sort) {
      const sortBy = req.query.sort.split(',').join(' ');
      query = query.sort(sortBy);
    } else {
      query = query.sort('bedNumber');
    }
    
    // Pagination
    const page = parseInt(req.query.page, 10) || 1;
    const limit = parseInt(req.query.limit, 10) || 25;
    const startIndex = (page - 1) * limit;
    const endIndex = page * limit;
    const total = await Bed.countDocuments();
    
    query = query.skip(startIndex).limit(limit);
    
    // Executing query
    const beds = await query;
    
    // Pagination result
    const pagination = {};
    
    if (endIndex < total) {
      pagination.next = {
        page: page + 1,
        limit
      };
    }
    
    if (startIndex > 0) {
      pagination.prev = {
        page: page - 1,
        limit
      };
    }
    
    res.status(200).json({
      success: true,
      count: beds.length,
      pagination,
      data: beds
    });
  } catch (err) {
    next(err);
  }
};

// @desc    Get single bed
// @route   GET /api/beds/:id
// @access  Private/Admin
exports.getBed = async (req, res, next) => {
  try {
    const bed = await Bed.findById(req.params.id).populate('roomId tenantId');
    
    if (!bed) {
      return res.status(404).json({
        success: false,
        message: 'Bed not found'
      });
    }
    
    res.status(200).json({
      success: true,
      data: bed
    });
  } catch (err) {
    next(err);
  }
};

// @desc    Create bed
// @route   POST /api/beds
// @access  Private/Admin
exports.createBed = async (req, res, next) => {
  try {
    // Check if room exists
    const room = await Room.findById(req.body.roomId);
    
    if (!room) {
      return res.status(404).json({
        success: false,
        message: 'Room not found'
      });
    }
    
    const bed = await Bed.create(req.body);
    
    res.status(201).json({
      success: true,
      data: bed
    });
  } catch (err) {
    next(err);
  }
};

// @desc    Update bed
// @route   PUT /api/beds/:id
// @access  Private/Admin
exports.updateBed = async (req, res, next) => {
  try {
    let bed = await Bed.findById(req.params.id);
    
    if (!bed) {
      return res.status(404).json({
        success: false,
        message: 'Bed not found'
      });
    }
    
    // If assigning a tenant
    if (req.body.tenantId) {
      // Check if tenant exists
      const tenant = await Tenant.findById(req.body.tenantId);
      
      if (!tenant) {
        return res.status(404).json({
          success: false,
          message: 'Tenant not found'
        });
      }
      
      // Check if bed is already occupied
      if (bed.status === 'occupied') {
        return res.status(400).json({
          success: false,
          message: 'Bed is already occupied'
        });
      }
      
      // Update tenant's bedId
      tenant.bedId = bed._id;
      await tenant.save();
      
      // Update bed status
      req.body.status = 'occupied';
    }
    
    // If unassigning a tenant
    if (req.body.status === 'vacant' && bed.tenantId) {
      // Remove bed reference from tenant
      const tenant = await Tenant.findById(bed.tenantId);
      tenant.bedId = null;
      await tenant.save();
      
      // Clear tenantId from bed
      req.body.tenantId = null;
    }
    
    bed = await Bed.findByIdAndUpdate(req.params.id, req.body, {
      new: true,
      runValidators: true
    });
    
    res.status(200).json({
      success: true,
      data: bed
    });
  } catch (err) {
    next(err);
  }
};

// @desc    Delete bed
// @route   DELETE /api/beds/:id
// @access  Private/Admin
exports.deleteBed = async (req, res, next) => {
  try {
    const bed = await Bed.findById(req.params.id);
    
    if (!bed) {
      return res.status(404).json({
        success: false,
        message: 'Bed not found'
      });
    }
    
    // If bed is occupied, unassign tenant first
    if (bed.status === 'occupied' && bed.tenantId) {
      const tenant = await Tenant.findById(bed.tenantId);
      tenant.bedId = null;
      await tenant.save();
    }
    
    await bed.remove();
    
    res.status(200).json({
      success: true,
      data: {}
    });
  } catch (err) {
    next(err);
  }
};