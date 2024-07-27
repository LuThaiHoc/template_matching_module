from PIL import Image, ImageDraw

def main():
    # Step 1: Read the TIFF image
    input_image_path = '/tmp/data/template_matching/hvkt_gmap_k05m.tif'  # Path to your input TIFF image
    image = Image.open(input_image_path)

    # Step 2: Modify the image
    # Create a drawing context
    draw = ImageDraw.Draw(image)

    # Define the polygon coordinates (in pixel units)
    polygon_pixels = [(100, 100), (150, 50), (200, 100), (150, 150)]

    # Draw the polygon on the image
    draw.polygon(polygon_pixels, outline='black', fill='lightblue')

    # Optionally, you can also draw other shapes or text here

    # Step 3: Save the modified image
    output_image_path = 'output_image.tif'  # Path to save the modified TIFF image
    image.save(output_image_path)

    # Optionally, show the image
    image.show()

if __name__ == "__main__":
    main()
    