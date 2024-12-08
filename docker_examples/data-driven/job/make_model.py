import tensorflow as tf
import tensorflow_probability as tfp
import tensorflow.keras.layers as tfkl

batchnorm_axis = -1

class RotationLayer(tfkl.Layer):
    def __init__(self, intensity, **kwargs):
        self.intensity = intensity
        super(RotationLayer, self).__init__(**kwargs)

    def call(self, x, training=None):
        def noised():
            batch = tf.shape(x)[0]
            randnormal = tf.random.normal((batch, 3, 3))
            qrinput = randnormal * self.intensity + (1.0 - self.intensity) * tf.eye(3)
            q = tfp.math.gram_schmidt(qrinput)
            return tf.transpose(tf.matmul(q, x, transpose_b=True), [0, 2, 1])

        # Use training argument to condition behavior based on the phase (training vs. inference)
        if training:
            return noised()
        else:
            return x

    def compute_output_shape(self, input_shape):
        return input_shape
    
    def get_config(self):
        config = {
                'intensity' : self.intensity,
                }
        base_config = super(RotationLayer, self).get_config()
        return dict(list(base_config.items()) + list(config.items()))

def block(filters, kernel_size, spatial_dropout, dropout, max_pool, gaussian_noise, mo):
    if batchnorm_axis is not None:
        mo = tfkl.BatchNormalization(axis=batchnorm_axis)(mo)
    if gaussian_noise > 0:
        mo = tfkl.GaussianNoise(gaussian_noise)(mo)
    if dropout > 0:
        mo = tfkl.Dropout(dropout)(mo)
    mo = tfkl.Conv1D(filters=filters, kernel_size=kernel_size)(mo)
    mo = tfkl.Activation(tf.nn.swish)(mo)
    if spatial_dropout > 0:
        mo = tfkl.SpatialDropout1D(spatial_dropout)(mo)
    if max_pool > 1:
        mo = tfkl.MaxPool1D(max_pool)(mo)
    return mo


def make_model(no_classes, amp_sdo, amp_do, amp_gn):
    
    model_input = tfkl.Input(shape=(None, 3),name='input')
    mo = model_input
    mo = RotationLayer(0.2)(mo)
    mo = block(filters = 16, kernel_size = 5, spatial_dropout = 0.2 * amp_sdo, dropout = 0.1 * amp_do, max_pool = 1, gaussian_noise = 0.01 * amp_gn, mo = mo)
    mo = block(filters = 16, kernel_size = 3, spatial_dropout = 0.2 * amp_sdo, dropout = 0.2 * amp_do, max_pool = 2, gaussian_noise = 0.02 * amp_gn, mo = mo)
    mo = block(filters = 32, kernel_size = 3, spatial_dropout = 0.2 * amp_sdo, dropout = 0.2 * amp_do, max_pool = 1, gaussian_noise = 0.05 * amp_gn, mo = mo)

    mo = block(64,  3, 0.2 * amp_sdo, 0.3 * amp_do, 2, 0.05 * amp_gn, mo)
    mo = tfkl.GlobalAveragePooling1D()(mo)

    mo = tfkl.Dropout(0.2 * amp_do)(mo)
    mo = tfkl.Dense(64)(mo)
    mo = tfkl.GaussianNoise(0.25)(mo) # comment out for general model
    mo = tfkl.ReLU()(mo)

    mo = tfkl.Dropout(0.2 * amp_do)(mo)
    mo = tfkl.Dense(32)(mo)
    mo = tfkl.GaussianNoise(0.25)(mo) # comment out for general model
    mo = tfkl.ReLU()(mo)

    mo = tfkl.Dense(no_classes)(mo)
    mo = tfkl.Softmax()(mo)
    
    model = tf.keras.models.Model(inputs=model_input, outputs=mo)
    
    return model