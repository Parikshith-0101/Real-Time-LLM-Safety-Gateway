import Joi from 'joi';

const sanitizeSchema = Joi.object({
  prompt: Joi.string().min(1).max(20000).required(),
  userId: Joi.string().optional()
});

export function validateSanitize(payload) {
  return sanitizeSchema.validate(payload, { abortEarly: false });
}
