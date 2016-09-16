import tensorflow as tf
import numpy as np
import utility


class HelperFunctionsTesT(tf.test.TestCase):
  def test_batch_queue_functionality(self):
    with self.test_session() as sess:
      foo = tf.RandomShuffleQueue(10, 0, [tf.float32, tf.int32], shapes=[[1, 2],
        [1]])
      batched = foo.dequeue_many(3)
      sess.run(foo.enqueue([[[3., 2.]], [6]]))
      sess.run(foo.enqueue([[[5., 3.]], [5]]))
      sess.run(foo.enqueue([[[5., 4.]], [4]]))
      sess.run(foo.enqueue([[[6., 5.]], [3]]))
      sess.run(foo.enqueue([[[7., 6.]], [2]]))
      sess.run(foo.enqueue([[[6., 5.]], [3]]))

      #res = sess.run(batched)
      #print(res)
      first = sess.run(batched[0])
      print(first)
      second = sess.run(batched[1])
      print(second)
      res = sess.run(batched)
      print(res)



class InceptionLayerTest(tf.test.TestCase):
  def test_layer_shape(self):
    with self.test_session():
      input_data = [[1., 5., 6.], [2., 4., 4.], [3., 7., 9.], [4., 9., 0.], [3., 7., 9.], [4., 9., 0.]]
      # Add an outer dimension to take the data from 1d to 2d
      input_data = tf.expand_dims(input_data, 0)
      # Add an outer dimension to take the data from unbatched to batch
      input_data = tf.expand_dims(input_data, 0)
      input_data_shape = tf.shape(input_data)
      self.assertAllEqual(input_data_shape.eval(), [1, 1, 6, 3])

      res = utility.inception_layer(input_data, 3, 2, 5)
      res_shape = tf.shape(res)

      tf.initialize_all_variables().run()

      self.assertAllEqual(res_shape.eval(), [1, 1, 3, 10])

class FixedTimeExtractTest(tf.test.TestCase):
  def test_cropped_extract(self):
    with self.test_session():
      input_data = [[1., 5.], [2., 4.], [3., 7.], [4., 9.], [5., 3.], [6., 8.], [7., 2.], [8., 9.]]
      expected_result = [[1., 5.], [2., 4.], [3., 7.], [4., 9.], [5., 3.], [6., 8.], [1., 5.], [2., 4.]]

      res = utility.fixed_time_extract(input_data, 5, 8)
      
      self.assertAllEqual(res.eval(), expected_result)

  def test_uncropped_extract(self):
    with self.test_session():
      input_data = [[1., 5., 6.], [2., 4., 4.], [3., 7., 9.], [4., 9., 0.]]

      res = utility.fixed_time_extract(input_data, 20, 4)
      self.assertAllEqual(res.eval(), input_data)

  def test_uncropped_extract_pad(self):
    with self.test_session():
      input_data = [[1., 5., 6.], [2., 4., 4.], [3., 7., 9.]]
      expected_result = [[1., 5., 6.], [2., 4., 4.], [3., 7., 9.], [1., 5., 6.], [2., 4., 4.]]

      res = utility.fixed_time_extract(input_data, 20, 5)
      self.assertAllEqual(res.eval(), expected_result)

  def test_random_fixed_time_extract(self):
    with self.test_session():
      input_data = [[1., 5., 6.], [2., 4., 4.], [3., 7., 9.]]
      
      res = utility.fixed_time_extract(input_data, 3, 6)
      res_shape = tf.shape(res)

      self.assertAllEqual(res_shape.eval(), [6, 3])

class PythonFixedTimeExtractTest(tf.test.TestCase):
  def test_cropped_extract(self):
    with self.test_session():
      input_data = np.array([[1., 5.], [2., 4.], [3., 7.], [4., 9.], [5., 3.],
        [6., 8.], [7., 2.], [8., 9.]])
      expected_result = np.array([[1., 5.], [2., 4.], [3., 7.], [4., 9.], [5.,
        3.], [6., 8.], [1., 5.], [2., 4.]])

      res = utility.np_array_fixed_time_extract(input_data, 5, 8)
      
      self.assertAllEqual(res, expected_result)

  def test_uncropped_extract(self):
    with self.test_session():
      input_data = np.array([[1., 5., 6.], [2., 4., 4.], [3., 7., 9.], [4., 9.,
        0.]])

      res = utility.np_array_fixed_time_extract(input_data, 20, 4)
      self.assertAllEqual(res, input_data)

  def test_uncropped_extract_pad(self):
    with self.test_session():
      input_data = np.array([[1., 5., 6.], [2., 4., 4.], [3., 7., 9.]])
      expected_result = np.array([[1., 5., 6.], [2., 4., 4.], [3., 7., 9.], [1.,
        5., 6.], [2., 4., 4.]])

      res = utility.np_array_fixed_time_extract(input_data, 20, 5)
      self.assertAllEqual(res, expected_result)

if __name__ == '__main__':
  tf.test.main()
