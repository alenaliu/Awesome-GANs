from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import tensorflow as tf
import numpy as np

import sys
import time

import cgan_model as cgan

sys.path.append('../')
import image_utils as iu
from datasets import MNISTDataSet as DataSet


results = {
    'output': './gen_img/',
    'model': './model/CGAN-model.ckpt'
}

train_step = {
    'global_step': 250001,
    'logging_interval': 2000,
}


def main():
    start_time = time.time()  # Clocking start

    # MNIST Dataset Load
    mnist = DataSet(ds_path="./").data

    # GPU configure
    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True

    with tf.Session(config=config) as s:
        # CGAN Model
        model = cgan.CGAN(s)

        # initializing
        s.run(tf.global_variables_initializer())

        sample_y = np.zeros(shape=[model.sample_num, model.n_classes])
        for i in range(10):
            sample_y[10 * i:10 * (i + 1), i] = 1

        d_overpowered = False
        for step in range(train_step['global_step']):
            batch_x, batch_y = mnist.train.next_batch(model.batch_size)
            batch_z = np.random.uniform(-1., 1., [model.batch_size, model.z_dim]).astype(np.float32)

            # Update D network
            if not d_overpowered:
                _, d_loss = s.run([model.d_op, model.d_loss],
                                  feed_dict={
                                      model.x: batch_x,
                                      model.c: batch_y,
                                      model.z: batch_z,
                                  })

            # Update G network
            _, g_loss = s.run([model.g_op, model.g_loss],
                              feed_dict={
                                  model.c: batch_y,
                                  model.z: batch_z,
                              })

            d_overpowered = d_loss < g_loss / 2.

            # Logging
            if step % train_step['logging_interval'] == 0:
                batch_x, batch_y = mnist.test.next_batch(model.batch_size)
                batch_z = np.random.uniform(-1., 1., [model.batch_size, model.z_dim]).astype(np.float32)

                d_loss, g_loss, summary = s.run([model.d_loss, model.g_loss, model.merged],
                                                feed_dict={
                                                    model.x: batch_x,
                                                    model.c: batch_y,
                                                    model.z: batch_z,
                                                })

                # Update d_overpowered
                d_overpowered = d_loss < g_loss / 2

                # Print Loss
                print("[+] Step %08d => " % step,
                      " D loss : {:.8f}".format(d_loss),
                      " G loss : {:.8f}".format(g_loss))

                # Training G model with sample image and noise
                sample_z = np.random.uniform(-1., 1., [model.sample_num, model.z_dim]).astype(np.float32)
                samples = s.run(model.g,
                                feed_dict={
                                    model.c: sample_y,
                                    model.z: sample_z,
                                })

                samples = np.reshape(samples, [-1, 28, 28, 1])

                # Summary saver
                model.writer.add_summary(summary, step)

                # Export image generated by model G
                sample_image_height = model.sample_size
                sample_image_width = model.sample_size
                sample_dir = results['output'] + 'train_{:08d}.png'.format(step)

                # Generated image save
                iu.save_images(samples,
                               size=[sample_image_height, sample_image_width],
                               image_path=sample_dir)

                # Model save
                model.saver.save(s, results['model'], global_step=step)

    end_time = time.time() - start_time  # Clocking end

    # Elapsed time
    print("[+] Elapsed time {:.8f}s".format(end_time))

    # Close tf.Session
    s.close()


if __name__ == '__main__':
    main()
