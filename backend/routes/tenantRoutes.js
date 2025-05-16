const express = require('express');
const {
  getTenants,
  getTenant,
  createTenant,
  updateTenant,
  deleteTenant,
  getTenantPayments
} = require('../controllers/tenantController');

const router = express.Router();

const { protect, authorize } = require('../middleware/auth');

router.route('/')
  .get(protect, authorize('admin'), getTenants)
  .post(protect, authorize('admin'), createTenant);

router.route('/:id')
  .get(protect, getTenant)
  .put(protect, updateTenant)
  .delete(protect, authorize('admin'), deleteTenant);

router.route('/:id/payments')
  .get(protect, getTenantPayments);

module.exports = router;