from py2rdf.describe.comp_descriptor import CompositionDescriptor

def binarycount(bits):

    count = 0
    for i, bit in enumerate(bits):
        if bit == 1:
            count = count + 2**i
    
    return count

if __name__ == "__main__":
  g, s = CompositionDescriptor().from_function(binarycount)
  print(g.serialize(format='turtle'))