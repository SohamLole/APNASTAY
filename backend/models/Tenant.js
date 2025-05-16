const mongoose = require('mongoose');

const tenantSchema = new mongoose.Schema({
  username: {
    type: String,
    required: true,
    unique: true,
    trim: true,
  },
  password: {
    type: String,
    required: true,
  },
  fullName: {
    type: String,
    required: true,
  },
  email: {
    type: String,
    required: true,
    unique: true,
  },
  phone: {
    type: String,
    required: true,
  },
  bedId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Bed',
  },
  rent: {
    type: Number,
    required: true,
  },
  deposit: {
    type: Number,
    required: true,
  },
  age: {
    type: Number,
    required: true,
  },
  gender: {
    type: String,
    enum: ['male', 'female', 'other'],
    required: true,
  },
  profession: {
    type: String,
    enum: ['student', 'worker'],
    required: true,
  },
  institute: {
    type: String,
    required: function() {
      return this.profession === 'student';
    },
  },
  company: {
    type: String,
    required: function() {
      return this.profession === 'worker';
    },
  },
  address: {
    type: String,
    required: true,
  },
  aadharFront: {
    type: String, // URL to image
  },
  aadharBack: {
    type: String, // URL to image
  },
  photo: {
    type: String, // URL to image
  },
  createdAt: {
    type: Date,
    default: Date.now,
  },
});

// Hash password before saving
tenantSchema.pre('save', async function(next) {
  if (!this.isModified('password')) return next();
  
  try {
    const salt = await bcrypt.genSalt(10);
    this.password = await bcrypt.hash(this.password, salt);
    next();
  } catch (err) {
    next(err);
  }
});

module.exports = mongoose.model('Tenant', tenantSchema);